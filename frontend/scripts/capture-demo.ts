/**
 * Records the demo video's clips: each take starts a fresh `btl serve` with a memory store, plays the app in headless
 * Chromium the way a viewer would, and records the clip's stretch with the DevTools screencast at full device pixels.
 * ffmpeg turns the frames into an MP4 at a constant 30 fps, and takes a still at each clip's key moment.
 *
 * Run from frontend/ after `npm run build`: `node scripts/capture-demo.ts [--dry] [--only 03,05] [--out DIR]`.
 * `--dry` records nothing and saves a screenshot at every beat instead, for checking the path before a real take.
 * `--reduced-motion` records as a viewer who asks for less motion, for checking that case; the video never uses it.
 *
 * The viewer id is fixed, so every take gets the same matches and the same questions. The answers below are the right
 * ones for that viewer's questions, in the order the app asks them; each is checked against the verdict on screen, and
 * a take stops if the app ever asks something else.
 */
import { spawn, execFileSync, type ChildProcess } from 'node:child_process'
import { mkdirSync, rmSync, writeFileSync, readFileSync, existsSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium, type Browser, type BrowserContext, type CDPSession, type Locator, type Page } from 'playwright'

const HERE = dirname(fileURLToPath(import.meta.url))
const ROOT = resolve(HERE, '../..')
const PORT = 8766
const BASE = `http://127.0.0.1:${String(PORT)}`

const VIEWER = '26d51fac9ab4b6c3360c04138ca8cdde'
const CLUB = 'Bakewell Badgers'
/** Match 1, then match 2 up to its full time. */
const ANSWERS = ['B', 'A', 'A', 'C', 'A', 'C', 'C', 'C', 'A', 'A', 'B', 'A', 'A', 'A', 'A']

const TAP_BLUE = '#9CC8F0'
const SCROLL_SPEED = 600
const FPS = 30

interface Device {
	name: string
	width: number
	height: number
	scale: number
	mobile: boolean
}

const PHONE: Device = { name: 'phone', width: 390, height: 844, scale: 3, mobile: true }
const DESKTOP: Device = { name: 'desktop', width: 1440, height: 900, scale: 2, mobile: false }

interface ClipResult {
	file: string
	viewport: string
	duration_s: number
	matchClock: string
	marks: Record<string, number>
}

const args = process.argv.slice(2)
const dry = args.includes('--dry')
const reducedMotion = args.includes('--reduced-motion') ? 'reduce' : 'no-preference'
const onlyArg = args.indexOf('--only')
const only = onlyArg === -1 ? null : (args[onlyArg + 1] ?? '').split(',')
const outArg = args.indexOf('--out')
const OUT = resolve(outArg === -1 ? join(ROOT, 'demo-captures') : (args[outArg + 1] ?? ''))
const WORK = join(OUT, '.frames')

const wanted = (clip: string) => only === null || only.some(prefix => clip.startsWith(prefix))
const sleep = (ms: number) => new Promise(done => setTimeout(done, ms))
const log = (message: string) => {
	console.log(`[capture] ${message}`)
}

// --- The server: a fresh memory store per take, so every take starts from nothing --------------------------------

const startServer = async (): Promise<ChildProcess> => {
	const server = spawn('uv', ['run', 'btl', 'serve', '--store', 'memory', '--port', String(PORT)], {
		cwd: join(ROOT, 'backend'),
		detached: true,
		stdio: 'ignore'
	})
	for (let i = 0; i < 600; i++) {
		try {
			if ((await fetch(`${BASE}/api/health`)).ok) return server
		} catch {
			// Not up yet.
		}
		await sleep(250)
	}
	throw new Error('btl serve did not start')
}

const stopServer = (server: ChildProcess) => {
	if (server.pid !== undefined) process.kill(-server.pid, 'SIGTERM')
}

// --- The browser ------------------------------------------------------------------------------------------------

/** A ring where each tap lands, for recording only: a headless browser shows no pointer. */
const tapMarker = (blue: string) => {
	addEventListener(
		'pointerdown',
		event => {
			const ring = document.createElement('div')
			Object.assign(ring.style, {
				position: 'fixed',
				left: `${String(event.clientX - 22)}px`,
				top: `${String(event.clientY - 22)}px`,
				width: '44px',
				height: '44px',
				borderRadius: '50%',
				border: `3px solid ${blue}`,
				background: `${blue}2e`,
				boxSizing: 'border-box',
				pointerEvents: 'none',
				zIndex: '2147483647',
				opacity: '0.95',
				transform: 'scale(0.85)',
				transition: 'opacity 400ms ease-out, transform 400ms ease-out'
			})
			document.documentElement.appendChild(ring)
			requestAnimationFrame(() => {
				requestAnimationFrame(() => {
					ring.style.opacity = '0'
					ring.style.transform = 'scale(1.15)'
				})
			})
			setTimeout(() => {
				ring.remove()
			}, 450)
		},
		true
	)
}

/** What Preferences would keep in this browser (Dark, 40×), and the fixed viewer id when the take has one. */
const presetStorage = ({ viewer }: { viewer: string | null }) => {
	if (sessionStorage.getItem('capture.preset') !== null) return
	sessionStorage.setItem('capture.preset', '1')
	localStorage.clear()
	if (viewer !== null) localStorage.setItem('btl.viewer', viewer)
	localStorage.setItem('btl.theme', 'dark')
	localStorage.setItem('btl.feedSpeed', '40')
}

const openContext = async (browser: Browser, device: Device, viewer: string | null): Promise<BrowserContext> => {
	const context = await browser.newContext({
		viewport: { width: device.width, height: device.height },
		deviceScaleFactor: device.scale,
		isMobile: device.mobile,
		hasTouch: device.mobile,
		colorScheme: 'dark',
		reducedMotion
	})
	await context.addInitScript(presetStorage, { viewer })
	await context.addInitScript(tapMarker, TAP_BLUE)
	return context
}

const openApp = async (context: BrowserContext): Promise<Page> => {
	const page = await context.newPage()
	await page.goto(BASE)
	await page.evaluate(() => document.fonts.ready.then(() => undefined))
	return page
}

// --- Recording ----------------------------------------------------------------------------------------------------

interface Frame {
	file: string
	at: number
}

/** Records one clip with the DevTools screencast, which sends a frame whenever the page repaints. */
class Recorder {
	private readonly frames: Frame[] = []
	private readonly marks: Record<string, number> = {}
	private cdp: CDPSession | null = null
	private started = 0
	private stopped = 0
	private pending: Promise<void>[] = []

	private readonly page: Page
	private readonly device: Device
	readonly name: string

	constructor(page: Page, device: Device, name: string) {
		this.page = page
		this.device = device
		this.name = name
	}

	private get dir() {
		return join(WORK, this.name)
	}

	async start() {
		this.started = Date.now() / 1000
		if (dry) return
		rmSync(this.dir, { recursive: true, force: true })
		mkdirSync(this.dir, { recursive: true })
		const cdp = await this.page.context().newCDPSession(this.page)
		this.cdp = cdp
		cdp.on('Page.screencastFrame', frame => {
			const file = join(this.dir, `${String(this.frames.length).padStart(6, '0')}.jpg`)
			this.frames.push({ file, at: frame.metadata.timestamp ?? Date.now() / 1000 })
			writeFileSync(file, Buffer.from(frame.data, 'base64'))
			this.pending.push(cdp.send('Page.screencastFrameAck', { sessionId: frame.sessionId }).then(() => undefined))
		})
		await cdp.send('Page.startScreencast', {
			format: 'jpeg',
			quality: 95,
			maxWidth: this.device.width * this.device.scale,
			maxHeight: this.device.height * this.device.scale,
			everyNthFrame: 1
		})
		while (this.frames.length === 0) await sleep(20)
		this.started = this.frames[0]?.at ?? this.started
	}

	/** Notes when a beat starts, in seconds into the clip; a dry run saves a screenshot there instead. */
	async mark(beat: string) {
		this.marks[beat] = Number((Date.now() / 1000 - this.started).toFixed(1))
		log(`${this.name} ${beat} at ${String(this.marks[beat])} s`)
		if (dry) {
			mkdirSync(join(OUT, 'dry'), { recursive: true })
			await this.page.screenshot({ path: join(OUT, 'dry', `${this.name}-${beat}.png`) })
		}
	}

	async stop(): Promise<{ duration: number; marks: Record<string, number> }> {
		this.stopped = Date.now() / 1000
		if (this.cdp !== null) {
			await this.cdp.send('Page.stopScreencast')
			await Promise.all(this.pending)
			await this.cdp.detach()
		}
		return { duration: Number((this.stopped - this.started).toFixed(1)), marks: this.marks }
	}

	/** Writes the frames out at a constant 30 fps: each frame is held until the next one came. */
	encode(still: string) {
		if (dry) return
		const lines = ['ffconcat version 1.0']
		this.frames.forEach((frame, i) => {
			const next = this.frames[i + 1]?.at ?? this.stopped
			lines.push(`file '${frame.file}'`, `duration ${Math.max(next - frame.at, 0.001).toFixed(4)}`)
		})
		const last = this.frames.at(-1)
		if (last !== undefined) lines.push(`file '${last.file}'`)
		const list = join(this.dir, 'frames.txt')
		writeFileSync(list, lines.join('\n') + '\n')
		const width = this.device.width * this.device.scale
		const height = this.device.height * this.device.scale
		const video = join(OUT, `${this.name}.mp4`)
		execFileSync('ffmpeg', [
			'-y',
			'-loglevel',
			'error',
			'-f',
			'concat',
			'-safe',
			'0',
			'-i',
			list,
			'-vf',
			`scale=${String(width)}:${String(height)}:flags=lanczos:in_range=pc:out_range=tv,fps=${String(FPS)},format=yuv420p`,
			'-r',
			String(FPS),
			'-c:v',
			'libx264',
			'-preset',
			'slow',
			'-crf',
			'14',
			'-color_range',
			'tv',
			'-an',
			'-movflags',
			'+faststart',
			video
		])
		const at = this.marks[still] ?? 0
		execFileSync('ffmpeg', [
			'-y',
			'-loglevel',
			'error',
			'-ss',
			at.toFixed(2),
			'-i',
			video,
			'-frames:v',
			'1',
			join(OUT, `${this.name}.png`)
		])
		rmSync(this.dir, { recursive: true, force: true })
		log(`${this.name}.mp4: ${String(this.frames.length)} screencast frames`)
	}
}

// --- Acting like a viewer -------------------------------------------------------------------------------------------

/** Taps or clicks an element. On a wide one the tap lands near its right end, so the ring stays clear of its words. */
const tap = async (page: Page, target: Locator, fromLeft: number | null = null) => {
	await target.waitFor({ state: 'visible', timeout: 30_000 })
	const box = await target.boundingBox()
	if (box === null) throw new Error('nothing to tap')
	const x = fromLeft !== null ? box.x + fromLeft : box.width >= 160 ? box.x + box.width - 32 : box.x + box.width / 2
	const y = box.y + box.height / 2
	const viewport = page.viewportSize()
	if (viewport !== null && (box.y < 0 || box.y + box.height > viewport.height)) {
		await scrollToElement(target, 'bottom', 24)
		await sleep(600)
		await tap(page, target, fromLeft)
		return
	}
	if (await page.evaluate(() => navigator.maxTouchPoints > 0)) {
		await page.touchscreen.tap(x, y)
	} else {
		await page.mouse.click(x, y)
	}
}

/** Scrolls the element into view at about 600 px a second, easing in and out, never jumping. */
const scrollTo = async (page: Page, selector: string, align: 'top' | 'bottom' = 'top', margin = 16) => {
	await scrollToElement(page.locator(selector).first(), align, margin)
}

const scrollToElement = async (target: Locator, align: 'top' | 'bottom', margin: number) => {
	await target.waitFor({ state: 'attached' })
	await target.evaluate(
		async (element, { align, margin, speed }) => {
			let scroller: Element | null = element.parentElement
			while (scroller !== null) {
				const style = getComputedStyle(scroller)
				if (/(auto|scroll)/.test(style.overflowY) && scroller.scrollHeight > scroller.clientHeight) break
				scroller = scroller.parentElement
			}
			const scrolling = scroller ?? document.scrollingElement ?? document.documentElement
			const view = scroller === null ? { top: 0, bottom: window.innerHeight } : scrolling.getBoundingClientRect()
			const box = element.getBoundingClientRect()
			const wanted = align === 'top' ? box.top - view.top - margin : box.bottom - view.bottom + margin
			const from = scrolling.scrollTop
			const to = Math.max(0, Math.min(from + wanted, scrolling.scrollHeight - scrolling.clientHeight))
			const distance = to - from
			const duration = (Math.abs(distance) / speed) * 1000
			if (duration < 1) return
			await new Promise<void>(done => {
				const begun = performance.now()
				const step = (now: number) => {
					const p = Math.min(1, (now - begun) / duration)
					const eased = p < 0.5 ? 2 * p * p : 1 - (-2 * p + 2) ** 2 / 2
					scrolling.scrollTo({ top: from + distance * eased, behavior: 'instant' })
					if (p < 1) requestAnimationFrame(step)
					else done()
				}
				requestAnimationFrame(step)
			})
		},
		{ align, margin, speed: SCROLL_SPEED }
	)
}

const button = (page: Page, text: string | RegExp) => page.locator('button:visible', { hasText: text }).first()
const optionTile = (page: Page, key: string) => page.locator('button[role=radio]:visible').nth('ABC'.indexOf(key))

class Viewer {
	private answered = 0
	private readonly page: Page

	constructor(page: Page) {
		this.page = page
	}

	get nextAnswer() {
		const key = ANSWERS.at(this.answered)
		if (key === undefined) throw new Error('no answer left for this question')
		return key
	}

	/** Picks the next answer and locks it in, at the pace the video wants when recording. */
	async answer(paced: Recorder | null, read = 2000) {
		const key = this.nextAnswer
		const page = this.page
		await page.locator('button.lock-in').waitFor({ state: 'visible' })
		if (paced !== null) await sleep(read)
		await tap(page, optionTile(page, key))
		if (paced !== null) {
			await paced.mark('pick')
			await sleep(1000)
		}
		const lock = page.locator('button.lock-in', { hasText: `Lock in ${key}` })
		await lock.waitFor({ state: 'visible' })
		if (paced !== null) await paced.mark('lockIn')
		await tap(page, lock)
		await page.locator('.feedback').waitFor({ state: 'visible', timeout: 30_000 })
		if (paced !== null) await paced.mark('reveal')
		const verdict = await page.locator('.feedback__verdict-text').innerText()
		if (verdict !== 'Right read.') throw new Error(`answer ${String(this.answered)} was not right: ${verdict}`)
		this.answered += 1
	}

	/** Plays on as a viewer would, skipping ahead in the feed, until `done` says to stop. Nothing here is recorded. */
	async playUntil(done: () => Promise<boolean>, what: string) {
		const page = this.page
		for (let i = 0; i < 300; i++) {
			if (await done()) return
			if ((await page.locator('button.lock-in:visible').count()) > 0) {
				await this.answer(null)
				continue
			}
			for (const selector of [
				'button.primary-button:visible',
				'button.feedback__continue:visible',
				'button.match-step__skip:visible'
			]) {
				const found = page.locator(selector).first()
				if ((await found.count()) > 0) {
					await found.click()
					break
				}
			}
			await sleep(400)
		}
		throw new Error(`never reached ${what}`)
	}
}

const visible = (locator: Locator) => async () => (await locator.count()) > 0 && locator.first().isVisible()

/** Picks the club and goes on to Matches, from the picker a new viewer sees. */
const pickClub = async (page: Page, recorder: Recorder | null) => {
	const club = page.locator('button.pick-team__club', { hasText: CLUB })
	await club.waitFor({ state: 'visible', timeout: 60_000 })
	if (recorder !== null) await sleep(1200)
	// On the crest, so the ring covers no words.
	await tap(page, club, 31)
	if (recorder !== null) {
		await recorder.mark('pickClub')
		await sleep(1500)
	}
	await scrollTo(page, '.pick-team__actions', 'bottom', 16)
	if (recorder !== null) await sleep(800)
	await tap(page, button(page, `Continue with ${CLUB}`))
	await page.getByRole('heading', { name: 'Matches' }).waitFor({ timeout: 60_000 })
}

// --- The takes ----------------------------------------------------------------------------------------------------

const clips: ClipResult[] = []

const finish = async (recorder: Recorder, device: Device, matchClock: string, still: string) => {
	const { duration, marks } = await recorder.stop()
	recorder.encode(still)
	clips.push({
		file: `${recorder.name}.mp4`,
		viewport: `${device.name} ${String(device.width)}x${String(device.height)} @${String(device.scale)}x`,
		duration_s: duration,
		matchClock,
		marks
	})
}

/** 02: the welcome's first three steps, then the club picker. A browser with no viewer id is the only way in. */
const takeWelcome = async (browser: Browser) => {
	const context = await openContext(browser, PHONE, null)
	const page = await openApp(context)
	await tap(page, button(page, 'Show me what I’ll learn'))
	await page.locator('.story-step__title').waitFor()
	await sleep(1500)
	const recorder = new Recorder(page, PHONE, '02-welcome')
	await recorder.start()
	await sleep(2000)
	for (let step = 1; step <= 3; step++) {
		await recorder.mark(`step${String(step)}`)
		await sleep(2600)
		if (step < 3) await tap(page, button(page, /^Next$/))
	}
	await tap(page, button(page, /^Skip$/))
	await recorder.mark('summary')
	await sleep(1200)
	await tap(page, button(page, /^Continue$/))
	await page.locator('button.pick-team__club').first().waitFor({ timeout: 60_000 })
	await recorder.mark('picker')
	await pickClub(page, recorder)
	await sleep(2000)
	await finish(recorder, PHONE, 'before match 1', 'pickClub')
	await context.close()
}

/** 03, 04 and 05 on the phone, in one viewer's run: match 1's first question, the level-up, match 2's live pass. */
const takePhone = async (browser: Browser) => {
	const context = await openContext(browser, PHONE, VIEWER)
	const page = await openApp(context)
	const viewer = new Viewer(page)
	await pickClub(page, null)

	const offered = page.locator('button.primary-button:visible', { hasText: /^(Make your read|See the question)$/ })
	await viewer.playUntil(visible(offered), 'the first question')
	if (wanted('03')) {
		await sleep(800)
		const recorder = new Recorder(page, PHONE, '03-dead-ball')
		await recorder.start()
		await sleep(2000)
		await tap(page, offered.first())
		await page.locator('button.lock-in').waitFor()
		await recorder.mark('question')
		await viewer.answer(recorder, 4000)
		await sleep(600)
		await recorder.mark('verdict')
		await sleep(3500)
		await scrollTo(page, '.feedback__explanation', 'top', 140)
		await recorder.mark('explanation')
		await sleep(8000)
		await scrollTo(page, '.feedback__understanding', 'bottom', 24)
		await recorder.mark('learnerCard')
		await sleep(4500)
		await sleep(2000)
		await finish(recorder, PHONE, 'match 1, 00:22', 'learnerCard')
	} else {
		await tap(page, offered.first())
		await viewer.answer(null)
	}

	const threat = page.locator('.story-step__title', { hasText: 'Follow the threat' })
	await viewer.playUntil(visible(threat), 'the line-breaking level-up')
	if (wanted('04')) {
		await sleep(800)
		const recorder = new Recorder(page, PHONE, '04-level-up')
		await recorder.start()
		await sleep(2000)
		await recorder.mark('threatGrid')
		await sleep(4000)
		await tap(page, button(page, /^Next$/))
		await page.getByRole('heading', { name: /^Ready for match 2/ }).waitFor()
		await recorder.mark('summary')
		await sleep(4000)
		await sleep(2000)
		await finish(recorder, PHONE, 'before match 2', 'summary')
	}

	const live = page.locator('button.primary-button:visible', { hasText: 'Make your read' })
	await viewer.playUntil(visible(live), 'the live pass question in match 2')
	if (wanted('05')) {
		await sleep(800)
		const recorder = new Recorder(page, PHONE, '05-live-pass')
		await recorder.start()
		await sleep(2000)
		await tap(page, live.first())
		await page.locator('button.lock-in').waitFor()
		await recorder.mark('question')
		await viewer.answer(recorder, 3500)
		await sleep(600)
		await recorder.mark('verdict')
		await sleep(3500)
		await scrollTo(page, '.feedback__explanation', 'top', 140)
		await recorder.mark('explanation')
		await sleep(5000)
		await scrollTo(page, '.feedback__understanding', 'bottom', 24)
		await recorder.mark('learnerLine')
		await sleep(4000)
		await sleep(2000)
		await finish(recorder, PHONE, `match 2, ${await page.locator('.feedback__clock').innerText()}`, 'reveal')
	}
	await context.close()
}

/** 01 and 06 on the desktop: the feed playing up to match 2's live question, then match 2's halftime report. */
const takeDesktop = async (browser: Browser) => {
	const context = await openContext(browser, DESKTOP, VIEWER)
	const page = await openApp(context)
	const viewer = new Viewer(page)
	await pickClub(page, null)

	// Match 2's first question is a review at 00:09; its feedback is where the clip starts, so the feed runs in full.
	const matchTwo = page.locator('.feedback__clock', { hasText: '00:09' })
	await viewer.playUntil(visible(matchTwo), 'match 2’s first answer')
	if (wanted('01')) {
		await sleep(800)
		const recorder = new Recorder(page, DESKTOP, '01-desktop-beside-match')
		await recorder.start()
		await sleep(2000)
		await tap(page, page.locator('button.feedback__continue'))
		await recorder.mark('feedPlays')
		const live = page.locator('button.primary-button:visible', { hasText: 'Make your read' })
		await live.waitFor({ timeout: 60_000 })
		await recorder.mark('offered')
		await sleep(3000)
		await sleep(2000)
		await finish(recorder, DESKTOP, 'match 2, 00:09 to 08:19', 'offered')
	}

	const report = page.locator('.report:visible')
	await viewer.playUntil(visible(report), 'match 2’s halftime report')
	if (wanted('06')) {
		await sleep(1200)
		const recorder = new Recorder(page, DESKTOP, '06-halftime')
		await recorder.start()
		await sleep(2000)
		// The score, the goals, the radar and the scout's note all fit the panel, so the report holds still.
		await recorder.mark('score')
		await sleep(4000)
		await recorder.mark('radar')
		await sleep(8000)
		await sleep(2000)
		await finish(recorder, DESKTOP, 'match 2, half-time', 'radar')
	}
	await context.close()
}

const commit = () => execFileSync('git', ['rev-parse', '--short', 'HEAD'], { cwd: ROOT }).toString().trim()

const main = async () => {
	mkdirSync(OUT, { recursive: true })
	const browser = await chromium.launch()
	const takes: [string[], (browser: Browser) => Promise<void>][] = [
		[['02'], takeWelcome],
		[['03', '04', '05'], takePhone],
		[['01', '06'], takeDesktop]
	]
	try {
		for (const [names, take] of takes) {
			if (!names.some(wanted)) continue
			const server = await startServer()
			try {
				await take(browser)
			} finally {
				stopServer(server)
				await sleep(500)
			}
		}
	} finally {
		await browser.close()
	}
	if (dry) return
	const manifestFile = join(OUT, 'manifest.json')
	const previous = existsSync(manifestFile)
		? (JSON.parse(readFileSync(manifestFile, 'utf8')) as { clips?: ClipResult[] })
		: {}
	const kept = (previous.clips ?? []).filter(clip => !clips.some(fresh => fresh.file === clip.file))
	const manifest = {
		...previous,
		commit: commit(),
		viewerId: VIEWER,
		club: 'BAK',
		clips: [...kept, ...clips].sort((a, b) => a.file.localeCompare(b.file))
	}
	writeFileSync(manifestFile, JSON.stringify(manifest, null, '\t') + '\n')
	rmSync(WORK, { recursive: true, force: true })
	log(`wrote ${manifestFile}`)
}

await main()
