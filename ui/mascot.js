/**
 * Switches Neo's supplied pixel-art mascot assets between idle and coding states.
 */
class MascotWidget {
    constructor(imageId) {
        this.image = document.getElementById(imageId);
        if (!this.image) return;

        this.subagentAssets = {
            doc_bot: 'assets/mascots/doc_bot_idle.png',
            data_bot: 'assets/mascots/data_bot_idle.png',
            code_bot: 'assets/mascots/code_bot_idle.png',
            artist_bot: 'assets/mascots/artist_bot_coding.png',
            server_bot: 'assets/mascots/server_bot_idle.png',
            launch_bot: 'assets/mascots/launch_bot_idle.png',
            cloud_bot: 'assets/mascots/cloud_bot_idle.png',
            fox_bot: 'assets/mascots/fox_bot_idle.png',
            crystal_bot: 'assets/mascots/crystal_bot_idle.png',
            cyber_cat: 'assets/mascots/cyber_cat_idle.png',
        };



        this.assets = {
            idle: 'assets/mascots/blue_bot_idle.png',
            coding: 'assets/mascots/blue_bot_coding.png',
        };
        this.setState('idle', 'System ready and waiting for prompt...');
    }

    setState(newState, label) {
        if (this.subagentAssets[newState]) {
            this.image.src = this.subagentAssets[newState];
        } else {
            const isCoding = ['thinking', 'executing', 'self_correcting', 'claw'].includes(newState);
            const visualState = isCoding ? 'coding' : 'idle';
            this.image.src = this.assets[visualState];
        }

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

