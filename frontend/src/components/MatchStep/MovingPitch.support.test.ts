import { trackAt, type Track } from './MovingPitch.support.ts'

// Two players; the away one isn't tracked at 12 s. The home player has the ball at 10 s, the away one at 12 s.
const track: Track = {
	players: [
		{ shirt: 7, home: true },
		{ shirt: 4, home: false }
	],
	frames: [
		{
			period: 1,
			at: 10,
			positions: [
				[40, 30],
				[60, 30]
			],
			on_ball: 0
		},
		{ period: 1, at: 12, positions: [[44, 34], null], on_ball: 1 }
	],
	ball: [
		{ period: 1, at: 10, point: [40, 30] },
		{ period: 1, at: 11, point: [60, 30] },
		{ period: 1, at: 12, point: [60, 30] }
	]
}

const homeAt = (at: number, smooth = true) => trackAt(track, at, smooth)?.players.find(p => p.home)?.at

test('players ease between keyframes and the ball moves steadily', () => {
	expect(homeAt(11)).toEqual([42, 32])
	// A quarter of the way through the gap, eased: 0.25² × (3 − 0.5) = 0.15625.
	expect(homeAt(10.5)).toEqual([40.625, 30.625])
	expect(trackAt(track, 10.5)?.ball).toEqual([50, 30])
})

test('before the first keyframe the pitch waits on it, and after the last it stays on the last', () => {
	expect(homeAt(0)).toEqual([40, 30])
	expect(homeAt(99)).toEqual([44, 34])
	expect(trackAt(track, 99)?.ball).toEqual([60, 30])
})

test('a player whose next position is unknown stays put, and one with no position is not drawn', () => {
	expect(trackAt(track, 11)?.players.find(p => !p.home)?.at).toEqual([60, 30])
	expect(trackAt(track, 12)?.players.map(p => p.shirt)).toEqual([7])
})

test('the player on the ball is the one making the action', () => {
	expect(trackAt(track, 11)?.players.map(p => p.onBall)).toEqual([true, false])
})

test('with reduced motion everything jumps from keyframe to keyframe', () => {
	expect(homeAt(11.9, false)).toEqual([40, 30])
	expect(homeAt(12, false)).toEqual([44, 34])
	expect(trackAt(track, 10.9, false)?.ball).toEqual([40, 30])
})

test('nothing glides across half-time', () => {
	const halves: Track = {
		...track,
		frames: [
			{
				period: 1,
				at: 2790,
				positions: [
					[40, 30],
					[60, 30]
				],
				on_ball: 0
			},
			{
				period: 2,
				at: 2800,
				positions: [
					[80, 30],
					[60, 30]
				],
				on_ball: 0
			}
		],
		ball: [
			{ period: 1, at: 2790, point: [40, 30] },
			{ period: 2, at: 2800, point: [52.5, 34] }
		]
	}

	expect(trackAt(halves, 2795)?.players[0]?.at).toEqual([40, 30])
	expect(trackAt(halves, 2795)?.ball).toEqual([40, 30])
	expect(trackAt(halves, 2800)?.players[0]?.at).toEqual([80, 30])
})

test('an empty track draws nothing', () => {
	expect(trackAt({ players: [], frames: [], ball: [] }, 10)).toBeNull()
})
