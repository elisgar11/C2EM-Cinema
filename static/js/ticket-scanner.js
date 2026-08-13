(() => {
    const startButton = document.getElementById("start-camera");
    const photoInput = document.getElementById("scanner-photo");
    const flashButton = document.getElementById("toggle-flash");
    const video = document.getElementById("scanner-video");
    const status = document.getElementById("camera-status");
    const shell = document.getElementById("camera-shell");
    const form = document.getElementById("scanner-form");
    const input = document.getElementById("scanner-value");

    if (!startButton || !photoInput || !video || !status || !form || !input) return;

    let scanner = null;
    let nativeStream = null;
    let nativeTimer = null;
    let submitting = false;

    function setStatus(message, tone = "neutral") {
        status.textContent = message;
        shell.dataset.scannerState = tone;
    }

    function errorName(error) {
        if (!error) return "";
        if (typeof error === "string") return error;
        return error.name || error.message || String(error);
    }

    function humanCameraError(error) {
        const name = errorName(error);
        if (/NotAllowedError|PermissionDeniedError|denied/i.test(name)) {
            return "El navegador ha bloqueado la cámara. Revisa el permiso de cámara para este sitio.";
        }
        if (/NotFoundError|DevicesNotFoundError|Camera not found/i.test(name)) {
            return "No se ha encontrado ninguna cámara disponible en este dispositivo.";
        }
        if (/NotReadableError|TrackStartError|Could not start/i.test(name)) {
            return "La cámara está ocupada por otra aplicación o el navegador no puede abrirla.";
        }
        if (/OverconstrainedError|ConstraintNotSatisfiedError/i.test(name)) {
            return "La cámara existe, pero no admite la configuración solicitada.";
        }
        if (/SecurityError|secure|https/i.test(name)) {
            return "El navegador exige HTTPS para utilizar la cámara en directo.";
        }
        return "No se pudo iniciar la cámara. Puedes usar «Escanear desde foto» o introducir el código manualmente.";
    }

    function canUseLiveCamera() {
        if (!window.isSecureContext) {
            setStatus(
                "La cámara en directo está bloqueada porque esta página usa HTTP. Abre C2EM mediante HTTPS o usa «Escanear desde foto».",
                "warning",
            );
            startButton.disabled = true;
            startButton.title = "La cámara web requiere HTTPS o localhost";
            return false;
        }
        if (!navigator.mediaDevices || typeof navigator.mediaDevices.getUserMedia !== "function") {
            setStatus(
                "Este navegador no expone acceso directo a la cámara. Usa «Escanear desde foto».",
                "warning",
            );
            startButton.disabled = true;
            return false;
        }
        return true;
    }

    async function stopNativeCamera() {
        if (nativeTimer) {
            clearTimeout(nativeTimer);
            nativeTimer = null;
        }
        if (nativeStream) {
            nativeStream.getTracks().forEach((track) => track.stop());
            nativeStream = null;
        }
        video.srcObject = null;
    }

    async function stopCamera() {
        if (scanner) {
            try {
                await scanner.stop();
            } catch (error) {
                console.debug("No se pudo detener QrScanner limpiamente", error);
            }
        }
        await stopNativeCamera();
        shell.classList.remove("is-active");
        flashButton.hidden = true;
        flashButton.textContent = "Encender linterna";
    }

    async function submitDecoded(value) {
        const decoded = String(value || "").trim();
        if (!decoded || submitting) return;
        submitting = true;
        setStatus("QR leído. Validando entrada…", "success");
        input.value = decoded;
        await stopCamera();
        form.submit();
    }

    async function startWithQrScanner() {
        if (!window.QrScanner) throw new Error("QrScanner no está disponible");

        if (!scanner) {
            scanner = new window.QrScanner(
                video,
                (result) => submitDecoded(result && typeof result === "object" ? result.data : result),
                {
                    preferredCamera: "environment",
                    maxScansPerSecond: 12,
                    returnDetailedScanResult: true,
                    highlightScanRegion: false,
                    highlightCodeOutline: true,
                    onDecodeError: (error) => {
                        if (window.QrScanner && error !== window.QrScanner.NO_QR_CODE_FOUND) {
                            console.debug("Error de lectura QR", error);
                        }
                    },
                },
            );
        }

        await scanner.start();
        shell.classList.add("is-active");
        setStatus("Cámara activa. Apunta al QR de la entrada.", "success");

        try {
            if (await scanner.hasFlash()) flashButton.hidden = false;
        } catch (error) {
            flashButton.hidden = true;
        }
    }

    async function startWithNativeDetector() {
        if (!("BarcodeDetector" in window)) throw new Error("BarcodeDetector no está disponible");
        if (window.BarcodeDetector.getSupportedFormats) {
            const formats = await window.BarcodeDetector.getSupportedFormats();
            if (!formats.includes("qr_code")) throw new Error("Este navegador no admite QR con BarcodeDetector");
        }

        const detector = new window.BarcodeDetector({ formats: ["qr_code"] });
        nativeStream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: { ideal: "environment" } },
            audio: false,
        });
        video.srcObject = nativeStream;
        await video.play();
        shell.classList.add("is-active");
        setStatus("Cámara activa. Apunta al QR de la entrada.", "success");

        const scan = async () => {
            if (!nativeStream || submitting) return;
            try {
                const codes = await detector.detect(video);
                if (codes.length && codes[0].rawValue) {
                    await submitDecoded(codes[0].rawValue);
                    return;
                }
            } catch (error) {
                console.debug("Error de lectura QR nativa", error);
            }
            nativeTimer = window.setTimeout(scan, 220);
        };
        scan();
    }

    async function startCamera() {
        if (!canUseLiveCamera()) return;

        startButton.disabled = true;
        setStatus("Solicitando permiso de cámara…");
        try {
            if (window.QrScanner) {
                await startWithQrScanner();
            } else {
                await startWithNativeDetector();
            }
        } catch (error) {
            await stopCamera();
            setStatus(humanCameraError(error), "danger");
            startButton.disabled = false;
            return;
        }
        startButton.textContent = "Cámara activa";
    }

    async function scanPhoto(file) {
        if (!file || submitting) return;
        setStatus("Leyendo QR de la imagen…");

        try {
            let result;
            if (window.QrScanner) {
                result = await window.QrScanner.scanImage(file, {
                    returnDetailedScanResult: true,
                    alsoTryWithoutScanRegion: true,
                });
                await submitDecoded(result && typeof result === "object" ? result.data : result);
                return;
            }

            if (!("BarcodeDetector" in window)) {
                throw new Error("No hay decodificador QR disponible en este navegador");
            }
            const bitmap = await createImageBitmap(file);
            try {
                const detector = new window.BarcodeDetector({ formats: ["qr_code"] });
                const codes = await detector.detect(bitmap);
                if (!codes.length || !codes[0].rawValue) throw new Error("No QR code found");
                await submitDecoded(codes[0].rawValue);
            } finally {
                bitmap.close?.();
            }
        } catch (error) {
            const name = errorName(error);
            const noCode = /No QR code found|No QR code/i.test(name);
            setStatus(
                noCode
                    ? "No se ha encontrado un QR legible en esa imagen. Acércate más y vuelve a intentarlo."
                    : "No se pudo leer esa imagen. Prueba otra foto o utiliza el código manual.",
                "danger",
            );
            photoInput.value = "";
        }
    }

    async function toggleFlash() {
        if (!scanner || flashButton.hidden) return;
        try {
            await scanner.toggleFlash();
            flashButton.textContent = scanner.isFlashOn() ? "Apagar linterna" : "Encender linterna";
        } catch (error) {
            flashButton.hidden = true;
        }
    }

    startButton.addEventListener("click", startCamera);
    photoInput.addEventListener("change", () => scanPhoto(photoInput.files && photoInput.files[0]));
    flashButton.addEventListener("click", toggleFlash);
    window.addEventListener("pagehide", () => {
        if (scanner) scanner.destroy();
        stopNativeCamera();
    });

    if (window.isSecureContext) {
        setStatus("Activa la cámara para leer códigos QR o usa «Escanear desde foto».");
    } else {
        canUseLiveCamera();
    }
})();
