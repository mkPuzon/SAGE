const ARXIV_CATEGORIES = {
  "cs.AI": "Artificial Intelligence",
  "cs.AR": "Hardware Architecture",
  "cs.CC": "Computational Complexity",
  "cs.CE": "Computational Engineering, Finance, and Science",
  "cs.CG": "Computational Geometry",
  "cs.CL": "Computation and Language",
  "cs.CR": "Cryptography and Security",
  "cs.CV": "Computer Vision and Pattern Recognition",
  "cs.CY": "Computers and Society",
  "cs.DB": "Databases",
  "cs.DC": "Distributed, Parallel, and Cluster Computing",
  "cs.DL": "Digital Libraries",
  "cs.DM": "Discrete Mathematics",
  "cs.DS": "Data Structures and Algorithms",
  "cs.ET": "Emerging Technologies",
  "cs.FL": "Formal Languages and Automata Theory",
  "cs.GL": "General Literature",
  "cs.GR": "Graphics",
  "cs.GT": "Computer Science and Game Theory",
  "cs.HC": "Human-Computer Interaction",
  "cs.IR": "Information Retrieval",
  "cs.IT": "Information Theory",
  "cs.LG": "Machine Learning",
  "cs.LO": "Logic in Computer Science",
  "cs.MA": "Multiagent Systems",
  "cs.MM": "Multimedia",
  "cs.MS": "Mathematical Software",
  "cs.NA": "Numerical Analysis",
  "cs.NE": "Neural and Evolutionary Computing",
  "cs.NI": "Networking and Internet Architecture",
  "cs.OH": "Other Computer Science",
  "cs.OS": "Operating Systems",
  "cs.PF": "Performance",
  "cs.PL": "Programming Languages",
  "cs.RO": "Robotics",
  "cs.SC": "Symbolic Computation",
  "cs.SD": "Sound",
  "cs.SE": "Software Engineering",
  "cs.SY": "Systems and Control",
  "econ.EM": "Econometrics",
  "econ.GN": "General Economics",
  "econ.TH": "Theoretical Economics",
  "eess.AS": "Audio and Speech Processing",
  "eess.IV": "Image and Video Processing",
  "eess.SP": "Signal Processing",
  "eess.SY": "Systems and Control",
  "math.AC": "Commutative Algebra",
  "math.AG": "Algebraic Geometry",
  "math.AP": "Analysis of PDEs",
  "math.AT": "Algebraic Topology",
  "math.CA": "Classical Analysis and ODEs",
  "math.CO": "Combinatorics",
  "math.CT": "Category Theory",
  "math.CV": "Complex Variables",
  "math.DG": "Differential Geometry",
  "math.DS": "Dynamical Systems",
  "math.FA": "Functional Analysis",
  "math.GM": "General Mathematics",
  "math.GN": "General Topology",
  "math.GR": "Group Theory",
  "math.GT": "Geometric Topology",
  "math.HO": "History and Overview",
  "math.IT": "Information Theory",
  "math.KT": "K-Theory and Homology",
  "math.LO": "Logic",
  "math.MG": "Metric Geometry",
  "math.MP": "Mathematical Physics",
  "math.NA": "Numerical Analysis",
  "math.NT": "Number Theory",
  "math.OA": "Operator Algebras",
  "math.OC": "Optimization and Control",
  "math.PR": "Probability",
  "math.QA": "Quantum Algebra",
  "math.RA": "Rings and Algebras",
  "math.RT": "Representation Theory",
  "math.SG": "Symplectic Geometry",
  "math.SP": "Spectral Theory",
  "math.ST": "Statistics Theory",
  "astro-ph.CO": "Cosmology and Nongalactic Astrophysics",
  "astro-ph.EP": "Earth and Planetary Astrophysics",
  "astro-ph.GA": "Astrophysics of Galaxies",
  "astro-ph.HE": "High Energy Astrophysical Phenomena",
  "astro-ph.IM": "Instrumentation and Methods for Astrophysics",
  "astro-ph.SR": "Solar and Stellar Astrophysics",
  "cond-mat.dis-nn": "Disordered Systems and Neural Networks",
  "cond-mat.mes-hall": "Mesoscale and Nanoscale Physics",
  "cond-mat.mtrl-sci": "Materials Science",
  "cond-mat.other": "Other Condensed Matter",
  "cond-mat.quant-gas": "Quantum Gases",
  "cond-mat.soft": "Soft Condensed Matter",
  "cond-mat.stat-mech": "Statistical Mechanics",
  "cond-mat.str-el": "Strongly Correlated Electrons",
  "cond-mat.supr-con": "Superconductivity",
  "gr-qc": "General Relativity and Quantum Cosmology",
  "hep-ex": "High Energy Physics - Experiment",
  "hep-lat": "High Energy Physics - Lattice",
  "hep-ph": "High Energy Physics - Phenomenology",
  "hep-th": "High Energy Physics - Theory",
  "math-ph": "Mathematical Physics",
  "nlin.AO": "Adaptation and Self-Organizing Systems",
  "nlin.CD": "Chaotic Dynamics",
  "nlin.CG": "Cellular Automata and Lattice Gases",
  "nlin.PS": "Pattern Formation and Solitons",
  "nlin.SI": "Exactly Solvable and Integrable Systems",
  "nucl-ex": "Nuclear Experiment",
  "nucl-th": "Nuclear Theory",
  "physics.acc-ph": "Accelerator Physics",
  "physics.ao-ph": "Atmospheric and Oceanic Physics",
  "physics.app-ph": "Applied Physics",
  "physics.atm-clus": "Atomic and Molecular Clusters",
  "physics.atom-ph": "Atomic Physics",
  "physics.bio-ph": "Biological Physics",
  "physics.chem-ph": "Chemical Physics",
  "physics.class-ph": "Classical Physics",
  "physics.comp-ph": "Computational Physics",
  "physics.data-an": "Data Analysis, Statistics and Probability",
  "physics.ed-ph": "Physics Education",
  "physics.flu-dyn": "Fluid Dynamics",
  "physics.gen-ph": "General Physics",
  "physics.geo-ph": "Geophysics",
  "physics.hist-ph": "History and Philosophy of Physics",
  "physics.ins-det": "Instrumentation and Detectors",
  "physics.med-ph": "Medical Physics",
  "physics.optics": "Optics",
  "physics.plasm-ph": "Plasma Physics",
  "physics.soc-ph": "Physics and Society",
  "physics.space-ph": "Space Physics",
  "quant-ph": "Quantum Physics",
  "q-bio.BM": "Biomolecules",
  "q-bio.CB": "Cell Behavior",
  "q-bio.GN": "Genomics",
  "q-bio.MN": "Molecular Networks",
  "q-bio.NC": "Neurons and Cognition",
  "q-bio.OT": "Other Quantitative Biology",
  "q-bio.PE": "Populations and Evolution",
  "q-bio.QM": "Quantitative Methods",
  "q-bio.SC": "Subcellular Processes",
  "q-bio.TO": "Tissues and Organs",
  "q-fin.CP": "Computational Finance",
  "q-fin.EC": "Economics",
  "q-fin.GN": "General Finance",
  "q-fin.MF": "Mathematical Finance",
  "q-fin.PM": "Portfolio Management",
  "q-fin.PR": "Pricing of Securities",
  "q-fin.RM": "Risk Management",
  "q-fin.ST": "Statistical Finance",
  "q-fin.TR": "Trading and Market Microstructure",
  "stat.AP": "Applications",
  "stat.CO": "Computation",
  "stat.ME": "Methodology",
  "stat.ML": "Machine Learning",
  "stat.OT": "Other Statistics",
  "stat.TH": "Statistics Theory",
};

function categoryName(tag) {
  return ARXIV_CATEGORIES[tag] || tag;
}

const searchInput = document.getElementById("search-input");
const resultsList = document.getElementById("results-list");
const modalOverlay = document.getElementById("modal-overlay");
const detailPanel = document.getElementById("detail-panel");

modalOverlay.addEventListener("click", (e) => {
  if (e.target === modalOverlay) closeModal();
});

function closeModal() {
  modalOverlay.classList.add("hidden");
  detailPanel.innerHTML = "";
}

let debounceTimer;

searchInput.addEventListener("input", (e) => {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => fetchKeywords(e.target.value.trim()), 250);
});

async function fetchKeywords(q) {
  try {
    const res = await fetch(`/api/keywords?q=${encodeURIComponent(q)}`);
    const data = await res.json();
    renderResults(data);
  } catch {
    resultsList.innerHTML = `<p class="empty-state">Could not reach API.</p>`;
  }
}

function renderResults(keywords) {
  closeModal();

  if (keywords.length === 0) {
    resultsList.innerHTML = `<p class="empty-state">No terms found.</p>`;
    return;
  }

  resultsList.innerHTML = keywords
    .map(
      (k) => `
      <div class="result-item" data-keyword="${escapeAttr(k.keyword)}">
        <span class="keyword-name">${escapeHtml(k.keyword)}</span>
        <span class="keyword-count">${k.count} paper${k.count !== 1 ? "s" : ""}</span>
      </div>`
    )
    .join("");

  resultsList.querySelectorAll(".result-item").forEach((el) => {
    el.addEventListener("click", () => fetchDetail(el.dataset.keyword));
  });
}

async function fetchDetail(keyword) {
  try {
    const res = await fetch(`/api/keywords/${encodeURIComponent(keyword)}`);
    if (!res.ok) {
      detailPanel.innerHTML = `<div class="modal-main"><p class="empty-state">Term not found.</p></div><aside class="modal-sidebar"></aside><button class="close-btn">&times;</button>`;
      detailPanel.querySelector(".close-btn").addEventListener("click", closeModal);
      modalOverlay.classList.remove("hidden");
      return;
    }
    const data = await res.json();
    renderDetail(data);
  } catch {
    detailPanel.innerHTML = `<div class="modal-main"><p class="empty-state">Could not load details.</p></div><aside class="modal-sidebar"></aside><button class="close-btn">&times;</button>`;
    detailPanel.querySelector(".close-btn").addEventListener("click", closeModal);
    modalOverlay.classList.remove("hidden");
  }
}

function renderDetail(data) {
  const articleCards = (data.articles || [])
    .map(
      (art) => `
      <div class="article-card">
        <div class="article-title">
          <a href="${escapeAttr(art.arxiv_url)}" target="_blank" rel="noopener">
            ${escapeHtml(art.title)}
          </a>
        </div>
        <div class="article-meta">
          <span class="article-date">${escapeHtml(art.date_submitted || "")}</span>
          ${(art.tags || []).map((t) => `<span class="tag" title="${escapeAttr(t)}">${escapeHtml(categoryName(t))}</span>`).join("")}
        </div>
        <p class="article-abstract">${escapeHtml(art.abstract || "")}</p>
      </div>`
    )
    .join("");

  const hasNewDefs = data.definition_simple && data.definition_technical;
  const definitionHtml = hasNewDefs
    ? `<div class="definition-toggle">
        <button class="def-toggle-btn active" data-mode="simple">Simple</button>
        <button class="def-toggle-btn" data-mode="technical">Technical</button>
       </div>
       <p class="detail-definition"
          data-simple="${escapeAttr(data.definition_simple)}"
          data-technical="${escapeAttr(data.definition_technical)}">
         ${escapeHtml(data.definition_simple)}
       </p>`
    : `<p class="detail-definition"></p>`;

  detailPanel.innerHTML = `
    <div class="modal-main">
      <div class="detail-header">
        <h2 class="detail-title">${escapeHtml(data.keyword)}</h2>
        <span class="detail-count">${data.count} paper${data.count !== 1 ? "s" : ""}</span>
      </div>
      ${definitionHtml}
      ${
        articleCards
          ? `<p class="articles-heading">Referenced in</p>
             <div class="article-cards">${articleCards}</div>`
          : ""
      }
    </div>
    <aside class="modal-sidebar">
      <p class="sidebar-heading">Related Terms</p>
      <div id="related-terms-list"></div>
    </aside>
    <button class="close-btn">&times;</button>
  `;
  detailPanel.querySelector(".close-btn").addEventListener("click", closeModal);
  detailPanel.querySelectorAll(".def-toggle-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      detailPanel.querySelectorAll(".def-toggle-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      const defEl = detailPanel.querySelector(".detail-definition");
      defEl.textContent = defEl.dataset[btn.dataset.mode];
    });
  });
  modalOverlay.classList.remove("hidden");
  fetchRelatedTerms(data.keyword);
}

async function fetchRelatedTerms(keyword) {
  const list = document.getElementById("related-terms-list");
  if (!list) return;
  try {
    const res = await fetch(`/api/keywords/${encodeURIComponent(keyword)}/related`);
    if (!res.ok) return;
    const terms = await res.json();
    if (!terms.length) return;
    list.innerHTML = terms
      .map((t) => `<div class="related-term-item" data-keyword="${escapeAttr(t.keyword)}">${escapeHtml(t.keyword)}</div>`)
      .join("");
    list.querySelectorAll(".related-term-item").forEach((el) => {
      el.addEventListener("click", () => fetchDetail(el.dataset.keyword));
    });
  } catch {
    // endpoint not yet implemented — sidebar stays empty
  }
}


function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function escapeAttr(str) {
  return String(str).replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

// Load all keywords on page start
fetchKeywords("");
