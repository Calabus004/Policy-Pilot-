// Zero-dependency Netlify Function: sends a follow-up email via Resend's HTTP API
// when someone finishes (or skips into) the waitlist assessment on the site.
// Requires RESEND_API_KEY (and optionally RESEND_FROM_EMAIL) as Netlify env vars.

exports.handler = async function (event) {
  if (event.httpMethod !== "POST") {
    return { statusCode: 405, body: "Method Not Allowed" };
  }

  let payload;
  try {
    payload = JSON.parse(event.body || "{}");
  } catch (err) {
    return { statusCode: 400, body: "Invalid JSON" };
  }

  // Honeypot: the site passes through its hidden field value. A filled value
  // means a bot filled in a field a human never sees — go quiet, no error.
  if (payload.hp) {
    return { statusCode: 200, body: JSON.stringify({ ok: true }) };
  }

  const name = (payload.name || "").trim();
  const email = (payload.email || "").trim();
  const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  if (!emailPattern.test(email)) {
    return { statusCode: 400, body: "Missing or invalid email" };
  }

  const apiKey = process.env.RESEND_API_KEY;
  const fromAddress = process.env.RESEND_FROM_EMAIL || "Policy Pilot <onboarding@resend.dev>";

  if (!apiKey) {
    console.error("RESEND_API_KEY is not set — skipping email send");
    return { statusCode: 200, body: JSON.stringify({ ok: false, reason: "email_not_configured" }) };
  }

  const firstName = name.split(" ")[0] || "there";

  try {
    const res = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        from: fromAddress,
        to: [email],
        subject: "You're on the Policy Pilot waitlist",
        html: buildEmailHtml(firstName)
      })
    });

    if (!res.ok) {
      const text = await res.text();
      console.error("Resend API error:", res.status, text);
      return { statusCode: 200, body: JSON.stringify({ ok: false, reason: "resend_error" }) };
    }

    return { statusCode: 200, body: JSON.stringify({ ok: true }) };
  } catch (err) {
    console.error("Failed to send email via Resend:", err);
    return { statusCode: 200, body: JSON.stringify({ ok: false, reason: "exception" }) };
  }
};

function buildEmailHtml(firstName) {
  return `<!doctype html>
<html>
<body style="margin:0; padding:0; background:#f4f5f7; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f4f5f7; padding:32px 16px;">
    <tr>
      <td align="center">
        <table role="presentation" width="480" cellpadding="0" cellspacing="0" style="background:#ffffff; border:1px solid #e3e6ec; border-radius:8px; max-width:480px; width:100%;">
          <tr>
            <td style="padding:28px 32px 0 32px;">
              <span style="font-family:'Courier New',monospace; font-size:12px; letter-spacing:2px; text-transform:uppercase; color:#b3862c;">POLICY PILOT</span>
            </td>
          </tr>
          <tr>
            <td style="padding:16px 32px 0 32px;">
              <h1 style="margin:0; font-size:20px; color:#1a1f2b;">Thanks, ${escapeHtml(firstName)} — you're on the list.</h1>
            </td>
          </tr>
          <tr>
            <td style="padding:16px 32px 0 32px; color:#4b5468; font-size:14px; line-height:1.6;">
              <p style="margin:0 0 14px;">We just wanted to confirm: you're signed up for early access to Policy Pilot, and we'll email you the moment it's ready.</p>
              <p style="margin:0 0 14px;">In the meantime, Policy Pilot automatically screens customers against UK &amp; EU sanctions lists, tracks FCA enforcement news, and keeps a plain-English audit trail — every day, without anyone lifting a finger.</p>
              <p style="margin:0;">No spam, no other emails between now and launch — just this one.</p>
            </td>
          </tr>
          <tr>
            <td style="padding:24px 32px 32px 32px;">
              <hr style="border:none; border-top:1px solid #e3e6ec; margin:0 0 16px;" />
              <p style="margin:0; font-size:12px; color:#9096a5;">Policy Pilot &middot; built for teams who take compliance seriously.</p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>`;
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
