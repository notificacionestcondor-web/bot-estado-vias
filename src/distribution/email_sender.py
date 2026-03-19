"""
Envío de boletín por correo electrónico (Gmail SMTP).

Envía el resumen HTML del boletín con el PDF adjunto
a la lista de destinatarios configurada.

Requiere:
- GMAIL_USER: dirección de correo Gmail
- GMAIL_APP_PASSWORD: App Password generada en Google Account
- EMAIL_RECIPIENTS: lista de correos separados por coma
"""

import os
import ssl
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime

from config import EMAIL_CONFIG, DESTINATARIOS, EMPRESA, MENSAJE_INSTITUCIONAL

logger = logging.getLogger(__name__)


def enviar_reporte(
    novedades: list,
    html_path: str,
    pdf_path: str = None,
    boletin_url: str = None,
) -> bool:
    """
    Envía el boletín por correo a todos los destinatarios.

    Args:
        novedades: Lista de novedades para generar resumen en el correo.
        html_path: Ruta del boletín HTML.
        pdf_path: Ruta del PDF adjunto (opcional).
        boletin_url: URL pública del boletín en GitHub Pages.

    Returns:
        True si el envío fue exitoso, False si falló.
    """
    sender = EMAIL_CONFIG["sender_email"]
    password = EMAIL_CONFIG["sender_password"]

    if not sender or not password:
        logger.warning("⚠️  Credenciales de correo no configuradas. Se omite el envío.")
        logger.info("   Configura GMAIL_USER y GMAIL_APP_PASSWORD en GitHub Secrets.")
        return False

    if not DESTINATARIOS:
        logger.warning("⚠️  No hay destinatarios configurados. Se omite el envío.")
        return False

    # Construir el correo
    now = datetime.now()
    subject = (
        f"📋 Boletín Estado de Vías - {EMPRESA} | "
        f"{now.strftime('%d/%m/%Y %I:%M %p')}"
    )

    html_body = _construir_resumen_correo(novedades, boletin_url)

    try:
        context = ssl.create_default_context()

        with smtplib.SMTP(EMAIL_CONFIG["smtp_server"], EMAIL_CONFIG["smtp_port"]) as server:
            server.starttls(context=context)
            server.login(sender, password)

            for destinatario in DESTINATARIOS:
                msg = MIMEMultipart("mixed")
                msg["From"] = f"{EMAIL_CONFIG['sender_name']} <{sender}>"
                msg["To"] = destinatario
                msg["Subject"] = subject

                # Cuerpo HTML
                msg.attach(MIMEText(html_body, "html", "utf-8"))

                # Adjuntar PDF si existe
                if pdf_path and os.path.exists(pdf_path):
                    with open(pdf_path, "rb") as f:
                        pdf_part = MIMEBase("application", "pdf")
                        pdf_part.set_payload(f.read())
                        encoders.encode_base64(pdf_part)
                        pdf_part.add_header(
                            "Content-Disposition",
                            f"attachment; filename={os.path.basename(pdf_path)}",
                        )
                        msg.attach(pdf_part)

                server.sendmail(sender, destinatario, msg.as_string())
                logger.info(f"   ✅ Correo enviado a: {destinatario}")

        logger.info(f"📨 Boletín enviado a {len(DESTINATARIOS)} destinatarios")
        return True

    except Exception as e:
        logger.error(f"❌ Error enviando correo: {e}")
        return False


def _construir_resumen_correo(novedades: list, boletin_url: str = None) -> str:
    """Genera el cuerpo HTML del correo con resumen de novedades."""

    alto = [n for n in novedades if n.get("nivel_impacto") == "alto"]
    medio = [n for n in novedades if n.get("nivel_impacto") == "medio"]
    bajo = [n for n in novedades if n.get("nivel_impacto") == "bajo"]

    novedades_html = ""

    for novedad in novedades:
        color = novedad.get("color_impacto", "#666")
        nivel = novedad.get("nivel_impacto", "bajo").upper()
        novedades_html += f"""
        <tr>
            <td style="padding:10px;border-bottom:1px solid #eee;">
                <span style="background:{color};color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:bold;">{nivel}</span>
            </td>
            <td style="padding:10px;border-bottom:1px solid #eee;font-weight:bold;">{novedad.get('corredor', '')}</td>
            <td style="padding:10px;border-bottom:1px solid #eee;">{novedad.get('tipo_novedad', '').title()}</td>
            <td style="padding:10px;border-bottom:1px solid #eee;">{novedad.get('estado', '')}</td>
        </tr>
        """

    link_boletin = ""
    if boletin_url:
        link_boletin = f"""
        <div style="text-align:center;margin:20px 0;">
            <a href="{boletin_url}" style="background:#1a56db;color:#fff;padding:12px 30px;border-radius:6px;text-decoration:none;font-weight:bold;display:inline-block;">
                Ver boletín completo
            </a>
        </div>
        """

    now = datetime.now()

    return f"""
    <div style="font-family:Arial,sans-serif;max-width:650px;margin:0 auto;color:#333;">
        <div style="background:#1e293b;padding:20px 24px;border-radius:8px 8px 0 0;">
            <h1 style="color:#fff;margin:0;font-size:18px;">🛣️ Boletín Estado de Vías</h1>
            <p style="color:#94a3b8;margin:4px 0 0;font-size:13px;">
                {EMPRESA} | {now.strftime('%d/%m/%Y')} — {now.strftime('%I:%M %p')}
            </p>
        </div>

        <div style="padding:20px 24px;background:#fff;border:1px solid #e2e8f0;">
            <div style="display:flex;gap:12px;margin-bottom:20px;">
                <div style="background:#fef2f2;border:1px solid #fecaca;padding:12px;border-radius:8px;text-align:center;flex:1;">
                    <div style="font-size:24px;font-weight:bold;color:#dc2626;">{len(alto)}</div>
                    <div style="font-size:11px;color:#991b1b;">IMPACTO ALTO</div>
                </div>
                <div style="background:#fffbeb;border:1px solid #fde68a;padding:12px;border-radius:8px;text-align:center;flex:1;">
                    <div style="font-size:24px;font-weight:bold;color:#f59e0b;">{len(medio)}</div>
                    <div style="font-size:11px;color:#92400e;">IMPACTO MEDIO</div>
                </div>
                <div style="background:#f0fdf4;border:1px solid #bbf7d0;padding:12px;border-radius:8px;text-align:center;flex:1;">
                    <div style="font-size:24px;font-weight:bold;color:#10b981;">{len(bajo)}</div>
                    <div style="font-size:11px;color:#065f46;">IMPACTO BAJO</div>
                </div>
            </div>

            <table style="width:100%;border-collapse:collapse;font-size:13px;">
                <thead>
                    <tr style="background:#f8fafc;">
                        <th style="padding:8px 10px;text-align:left;font-size:11px;color:#64748b;">IMPACTO</th>
                        <th style="padding:8px 10px;text-align:left;font-size:11px;color:#64748b;">CORREDOR</th>
                        <th style="padding:8px 10px;text-align:left;font-size:11px;color:#64748b;">NOVEDAD</th>
                        <th style="padding:8px 10px;text-align:left;font-size:11px;color:#64748b;">ESTADO</th>
                    </tr>
                </thead>
                <tbody>{novedades_html}</tbody>
            </table>

            {link_boletin}
        </div>

        <div style="background:#f8fafc;padding:16px 24px;border-radius:0 0 8px 8px;border:1px solid #e2e8f0;border-top:none;">
            <p style="margin:0;font-size:12px;color:#64748b;font-style:italic;">
                {MENSAJE_INSTITUCIONAL}
            </p>
        </div>
    </div>
    """
