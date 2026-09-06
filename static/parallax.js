(() => {
    const layer = document.querySelector('.parallax-bg');
    if (!layer) return;
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    const finePointer = window.matchMedia('(hover: hover) and (pointer: fine)');
    let x = 0;
    let y = 0;
    let frame = null;

    function render() {
        frame = null;
        if (reducedMotion.matches) {
            layer.style.transform = 'none';
            return;
        }
        const scroll = Math.min(Math.max(window.scrollY, 0) * 0.06, 24);
        layer.style.transform = `translate3d(${x}px, ${y - scroll}px, 0)`;
    }

    function schedule() {
        if (frame === null) frame = window.requestAnimationFrame(render);
    }

    function reset() {
        x = 0;
        y = 0;
        schedule();
    }

    window.addEventListener('pointermove', (event) => {
        if (reducedMotion.matches || !finePointer.matches || event.pointerType !== 'mouse') return;
        x = (event.clientX / window.innerWidth - 0.5) * 32;
        y = (event.clientY / window.innerHeight - 0.5) * 24;
        schedule();
    }, {passive: true});
    window.addEventListener('scroll', () => {
        if (!reducedMotion.matches) schedule();
    }, {passive: true});
    document.documentElement.addEventListener('pointerleave', reset);
    window.addEventListener('blur', reset);
    window.addEventListener('resize', reset);
    reducedMotion.addEventListener('change', reset);
    finePointer.addEventListener('change', reset);
    schedule();
})();
