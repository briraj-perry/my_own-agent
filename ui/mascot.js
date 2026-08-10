/**
 * MascotWidget: Animated Canvas Pixel-Art Terminal Robot Mascot for my_neo-agent
 * Features states: idle, thinking, permission, executing, self_correcting, success
 */
class MascotWidget {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) return;
        this.ctx = this.canvas.getContext('2d');
        
        this.state = 'idle'; // idle | thinking | permission | executing | self_correcting | success
        this.statusText = "System ready and waiting for prompt...";
        
        this.width = this.canvas.width;
        this.height = this.canvas.height;
        this.tick = 0;
        
        // Face expressions per state
        this.faceExpressions = {
            idle: "> _",
            thinking: "> _",
            permission: "! ?",
            executing: "> >",
            self_correcting: "> ~",
            success: "^ ^"
        };

        // Particles array for ambient/state effects
        this.particles = [];
        for (let i = 0; i < 20; i++) {
            this.particles.push({
                x: Math.random() * this.width,
                y: Math.random() * this.height,
                size: Math.random() * 3 + 1,
                speedY: Math.random() * 0.8 + 0.2,
                opacity: Math.random() * 0.7 + 0.3
            });
        }

        // Start animation loop
        this.animate = this.animate.bind(this);
        requestAnimationFrame(this.animate);
    }

    setState(newState, label) {
        this.state = newState;
        if (label) {
            this.statusText = label;
        }
        
        // Update DOM badge if present
        const badge = document.getElementById('mascot-state-badge');
        if (badge) {
            badge.className = `state-badge ${newState}`;
            badge.textContent = newState.replace('_', ' ').toUpperCase();
        }

        const footerText = document.getElementById('mascot-status-text');
        if (footerText && label) {
            footerText.textContent = label;
        }
    }

    drawRobot(timeOffset) {
        const ctx = this.ctx;
        const centerX = this.width / 2;
        
        // Vertical floating animation
        let floatY = Math.sin(timeOffset * 0.05) * 6;
        if (this.state === 'success') {
            floatY = Math.sin(timeOffset * 0.2) * 12; // Cheerful fast bounce
        } else if (this.state === 'permission') {
            floatY = Math.sin(timeOffset * 0.1) * 3; // Nervous jitter
        }
        
        const robotY = this.height / 2 - 10 + floatY;

        // 1. Draw Glow Aura
        ctx.save();
        ctx.beginPath();
        let auraColor = "rgba(157, 78, 221, 0.25)";
        let glowBlur = 25;
        
        if (this.state === 'thinking') {
            auraColor = "rgba(76, 201, 240, 0.35)";
        } else if (this.state === 'permission') {
            auraColor = "rgba(255, 0, 85, 0.45)";
            glowBlur = 35 + Math.sin(timeOffset * 0.15) * 10;
        } else if (this.state === 'executing') {
            auraColor = "rgba(0, 245, 212, 0.35)";
        } else if (this.state === 'self_correcting') {
            auraColor = "rgba(255, 183, 3, 0.35)";
        } else if (this.state === 'success') {
            auraColor = "rgba(0, 245, 212, 0.5)";
            glowBlur = 40;
        }

        ctx.arc(centerX, robotY, 65, 0, Math.PI * 2);
        ctx.fillStyle = auraColor;
        ctx.shadowColor = auraColor;
        ctx.shadowBlur = glowBlur;
        ctx.fill();
        ctx.restore();

        // 2. Robot Antenna
        ctx.fillStyle = "#9d4edd";
        ctx.fillRect(centerX - 3, robotY - 65, 6, 14);
        
        // Antenna orb tip
        ctx.beginPath();
        let tipColor = "#00f5d4";
        if (this.state === 'permission') tipColor = "#ff0055";
        if (this.state === 'self_correcting') tipColor = "#ffb703";
        ctx.arc(centerX, robotY - 70, 7, 0, Math.PI * 2);
        ctx.fillStyle = tipColor;
        ctx.shadowColor = tipColor;
        ctx.shadowBlur = 12;
        ctx.fill();
        ctx.shadowBlur = 0;

        // 3. Robot Head / Monitor Body (Pixel Art Box)
        const headW = 100;
        const headH = 75;
        const headX = centerX - headW / 2;
        const headY = robotY - 50;

        // Outer Head Casing
        ctx.fillStyle = "#1e1435";
        ctx.strokeStyle = "#9d4edd";
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.roundRect(headX, headY, headW, headH, 12);
        ctx.fill();
        ctx.stroke();

        // Inner Screen Box
        const screenMargin = 8;
        const screenX = headX + screenMargin;
        const screenY = headY + screenMargin;
        const screenW = headW - screenMargin * 2;
        const screenH = headH - screenMargin * 2;

        let screenBg = "#07050e";
        if (this.state === 'permission') screenBg = "#1a000a";
        ctx.fillStyle = screenBg;
        ctx.beginPath();
        ctx.roundRect(screenX, screenY, screenW, screenH, 8);
        ctx.fill();

        // Screen Matrix Scanlines
        ctx.fillStyle = "rgba(157, 78, 221, 0.08)";
        for (let i = screenY; i < screenY + screenH; i += 4) {
            ctx.fillRect(screenX, i, screenW, 1);
        }

        // 4. Render Face Expression on Monitor Screen
        ctx.font = "bold 20px 'Fira Code', monospace";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";

        let faceStr = this.faceExpressions[this.state] || "> _";
        let faceColor = "#00f5d4";

        if (this.state === 'idle') {
            // Blinking cursor in idle mode
            const blink = Math.floor(timeOffset / 20) % 2 === 0;
            faceStr = blink ? "> _" : ">  ";
            faceColor = "#00f5d4";
        } else if (this.state === 'thinking') {
            // Matrix scrolling cursor
            const chars = ["> _", "> .", "> ..", "> ...", "> -"];
            faceStr = chars[Math.floor(timeOffset / 8) % chars.length];
            faceColor = "#4cc9f0";
        } else if (this.state === 'permission') {
            faceStr = "! ?";
            faceColor = "#ff0055";
        } else if (this.state === 'executing') {
            faceStr = (Math.floor(timeOffset / 10) % 2 === 0) ? "> >" : "> _";
            faceColor = "#00f5d4";
        } else if (this.state === 'self_correcting') {
            faceStr = "> ~";
            faceColor = "#ffb703";
        } else if (this.state === 'success') {
            faceStr = "^ ^";
            faceColor = "#00f5d4";
        }

        ctx.fillStyle = faceColor;
        ctx.shadowColor = faceColor;
        ctx.shadowBlur = 10;
        ctx.fillText(faceStr, centerX, screenY + screenH / 2);
        ctx.shadowBlur = 0;

        // 5. Robot Body / Torso
        const bodyW = 70;
        const bodyH = 45;
        const bodyX = centerX - bodyW / 2;
        const bodyY = headY + headH + 6;

        ctx.fillStyle = "#140f26";
        ctx.strokeStyle = "#7b2cbf";
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.roundRect(bodyX, bodyY, bodyW, bodyH, 8);
        ctx.fill();
        ctx.stroke();

        // Chest Emblem: "> -"
        ctx.font = "bold 13px 'Fira Code', monospace";
        ctx.fillStyle = "#f72585";
        ctx.fillText("> -", centerX, bodyY + bodyH / 2);

        // Robot Arms
        ctx.strokeStyle = "#9d4edd";
        ctx.lineWidth = 4;
        
        // Left arm
        ctx.beginPath();
        ctx.moveTo(bodyX - 2, bodyY + 10);
        ctx.lineTo(bodyX - 16, bodyY + 24 + Math.sin(timeOffset * 0.1) * 4);
        ctx.stroke();

        // Right arm
        ctx.beginPath();
        ctx.moveTo(bodyX + bodyW + 2, bodyY + 10);
        ctx.lineTo(bodyX + bodyW + 16, bodyY + 24 - Math.sin(timeOffset * 0.1) * 4);
        ctx.stroke();
    }

    drawParticles(timeOffset) {
        const ctx = this.ctx;
        for (let p of this.particles) {
            p.y -= p.speedY;
            if (p.y < 0) {
                p.y = this.height;
                p.x = Math.random() * this.width;
            }

            ctx.beginPath();
            ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
            
            let pColor = `rgba(157, 78, 221, ${p.opacity})`;
            if (this.state === 'executing') pColor = `rgba(0, 245, 212, ${p.opacity})`;
            if (this.state === 'permission') pColor = `rgba(255, 0, 85, ${p.opacity})`;
            if (this.state === 'self_correcting') pColor = `rgba(255, 183, 3, ${p.opacity})`;

            ctx.fillStyle = pColor;
            ctx.fill();
        }
    }

    animate() {
        this.tick++;
        this.ctx.clearRect(0, 0, this.width, this.height);
        
        this.drawParticles(this.tick);
        this.drawRobot(this.tick);

        requestAnimationFrame(this.animate);
    }
}

// Initialize Global Mascot Instance
window.addEventListener('DOMContentLoaded', () => {
    window.mascot = new MascotWidget('mascot-canvas');
});
