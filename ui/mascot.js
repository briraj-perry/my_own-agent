/**
 * Switches Neo's supplied pixel-art mascot assets between idle and coding states.
 */
class MascotWidget {
    constructor(imageId) {
        this.image = document.getElementById(imageId);
        if (!this.image) return;

        this.assets = {
            idle: 'assets/mascots/blue_bot_idle.png',
            coding: 'assets/mascots/blue_bot_coding.png',
        };
        this.setState('idle', 'System ready and waiting for prompt...');
    }

    setState(newState, label) {
        const isCoding = ['thinking', 'executing', 'self_correcting'].includes(newState);
        const visualState = isCoding ? 'coding' : 'idle';

        this.image.src = this.assets[visualState];
        this.image.alt = visualState === 'coding' ? 'Neo coding mascot' : 'Neo idle mascot';
        this.image.className = `mascot-image ${visualState}`;

        const badge = document.getElementById('mascot-state-badge');
        if (badge) {
            badge.className = `state-badge ${newState}`;
            badge.textContent = newState.replace('_', ' ').toUpperCase();
        }

        const footerText = document.getElementById('mascot-status-text');
        if (footerText && label) footerText.textContent = label;
    }
}

window.addEventListener('DOMContentLoaded', () => {
    window.mascot = new MascotWidget('mascot-image');
});
