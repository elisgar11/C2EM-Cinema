# Escáner QR

El lector de entradas dispone de tres modos:

1. cámara en directo;
2. escaneo desde una foto tomada o elegida en el dispositivo;
3. introducción manual del código, UUID o URL de la entrada.

## Por qué la cámara puede no arrancar

Los navegadores solo permiten `getUserMedia()` en un contexto seguro. En la práctica, la cámara en directo necesita HTTPS o una URL local como `http://localhost`.

Una URL remota como:

```text
http://100.x.x.x:8000/staff/scanner/
```

no se considera un contexto seguro aunque el tráfico viaje dentro de una VPN cifrada. En ese caso C2EM desactiva el botón de vídeo en directo y mantiene disponibles el escaneo desde foto y el código manual.

## Tailscale

Si el servidor C2EM ya está dentro de una tailnet, la forma recomendada es publicar el puerto local mediante Tailscale Serve. Primero habilita MagicDNS y HTTPS Certificates en la consola de Tailscale. Después, en el equipo que ejecuta C2EM:

```bash
tailscale serve --bg localhost:8000
```

Tailscale mostrará una URL HTTPS con el dominio `*.ts.net`. Abre C2EM desde esa URL en el móvil. El navegador verá un certificado TLS válido y podrá solicitar permiso para la cámara.

Si Docker está publicado en otro puerto del host, sustituye `8000` por ese puerto. Por ejemplo:

```bash
tailscale serve --bg localhost:8085
```

Puedes revisar la configuración con:

```bash
tailscale serve status
```

## Compatibilidad del decodificador

C2EM empaqueta `qr-scanner` 1.4.2 dentro de la imagen Docker. El navegador usa `BarcodeDetector` cuando lo soporta y el worker del propio paquete como fallback cuando no lo soporta. El navegador no necesita cargar scripts desde un CDN.

La opción **Escanear desde foto** utiliza el mismo decodificador y es útil cuando la política de seguridad del navegador no permite abrir un stream de vídeo.

## Diagnóstico rápido

Si la cámara sigue sin arrancar sobre HTTPS:

- comprueba el permiso de cámara del sitio en el navegador;
- cierra otras aplicaciones que estén usando la cámara;
- recarga la página después de cambiar permisos;
- prueba `Escanear desde foto` para separar un problema de permisos de un problema de lectura del QR.
