const form = document.querySelector("#analysis-form");
const result = document.querySelector("#result");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  result.innerHTML = "<p>Running analysis...</p>";

  const response = await fetch("/api/v1/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      category: document.querySelector("#category").value,
      minimum_value: Number(document.querySelector("#minimum-value").value),
    }),
  });

  if (!response.ok) {
    result.innerHTML = "<p role='alert'>Analysis failed.</p>";
    return;
  }

  const payload = await response.json();
  result.innerHTML = [
    "<p class='eyebrow'>Verified result</p>",
    "<dl>",
    "<div><dt>Count</dt><dd data-testid='count'>" + payload.count + "</dd></div>",
    "<div><dt>Total</dt><dd data-testid='total'>" + payload.total + "</dd></div>",
    "<div><dt>Average</dt><dd data-testid='average'>" + payload.average + "</dd></div>",
    "</dl>",
    "<details><summary>Provenance</summary><code>" + payload.input_sha256 + "</code></details>",
  ].join("");
});
