import '@testing-library/jest-dom/vitest'

// jsdom has no modal dialogs yet; these set `open`, move focus in and fire `close` as the browser does. Tests run in
// node have no DOM at all.
if (typeof HTMLDialogElement !== 'undefined') {
	HTMLDialogElement.prototype.showModal = function (this: HTMLDialogElement) {
		this.open = true
		this.querySelector('button')?.focus()
	}
	HTMLDialogElement.prototype.close = function (this: HTMLDialogElement) {
		this.open = false
		this.dispatchEvent(new Event('close'))
	}
}
