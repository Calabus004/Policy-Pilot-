// Zero-dependency Netlify Function powering the internal dashboard
// (web/dashboard.html). Validates a shared passphrase, then pulls both
// forms' submissions from Netlify's own Submissions API and returns them
// as JSON. Requires DASHBOARD_PASSWORD and NETLIFY_API_TOKEN env vars.

exports.handler = async function (event) {
  if (event.httpMethod !== "POST") {
    return { statusCode: 405, body: JSON.stringify({ error: "Method Not Allowed" }) };
  }

  let payload;
  try {
    payload = JSON.parse(event.body || "{}");
  } catch (err) {
    return { statusCode: 400, body: JSON.stringify({ error: "Invalid JSON" }) };
  }

  const dashboardPassword = process.env.DASHBOARD_PASSWORD;
  if (!dashboardPassword) {
    return { statusCode: 500, body: JSON.stringify({ error: "DASHBOARD_PASSWORD is not configured" }) };
  }
  if (payload.password !== dashboardPassword) {
    return { statusCode: 401, body: JSON.stringify({ error: "Incorrect password" }) };
  }

  const token = process.env.NETLIFY_API_TOKEN;
  const siteId = process.env.SITE_ID || process.env.NETLIFY_SITE_ID;
  if (!token || !siteId) {
    return { statusCode: 500, body: JSON.stringify({ error: "NETLIFY_API_TOKEN or site ID is not configured" }) };
  }

  try {
    const formsRes = await fetch(`https://api.netlify.com/api/v1/sites/${siteId}/forms`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    if (!formsRes.ok) {
      throw new Error("Failed to list forms: " + formsRes.status);
    }
    const forms = await formsRes.json();

    const startedForm = forms.find((f) => f.name === "assessment-started");
    const completedForm = forms.find((f) => f.name === "assessment-completed");

    async function fetchSubmissions(form) {
      if (!form) return [];
      const res = await fetch(`https://api.netlify.com/api/v1/forms/${form.id}/submissions`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (!res.ok) return [];
      return res.json();
    }

    const [startedSubs, completedSubs] = await Promise.all([
      fetchSubmissions(startedForm),
      fetchSubmissions(completedForm)
    ]);

    return {
      statusCode: 200,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        started: startedSubs.map((s) => ({
          name: s.data.name,
          email: s.data.email,
          created_at: s.created_at
        })),
        completed: completedSubs.map((s) => ({
          name: s.data.name,
          email: s.data.email,
          path: s.data.path,
          consent: s.data.consent,
          fit_score: s.data.fit_score,
          fit_tier: s.data.fit_tier,
          comms: s.data.comms,
          docs: s.data.docs,
          news: s.data.news,
          owner: s.data.owner,
          frustration: s.data.frustration,
          missed: s.data.missed,
          toolvalue: s.data.toolvalue,
          payoff: s.data.payoff,
          risk_score: s.data.risk_score,
          risk_tier: s.data.risk_tier,
          low_risk_feedback: s.data.low_risk_feedback,
          created_at: s.created_at
        }))
      })
    };
  } catch (err) {
    console.error("get-submissions failed:", err);
    return { statusCode: 502, body: JSON.stringify({ error: "Failed to fetch submissions from Netlify" }) };
  }
};
