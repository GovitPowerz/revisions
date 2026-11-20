/**
 * Révisions: a small static quiz site.
 *
 * Three views, selected by the URL hash:
 *   #/                       list of subjects
 *   #/<subject>              list of topics of a subject, then its exercise series
 *   #/<subject>/<topic>      the quiz itself
 *
 * Content lives in JSON files: quiz/catalogue.json lists subjects, their topics
 * and their exercise series; each topic points to one quiz file and each series
 * to one PDF. Adding a quiz or a series needs no code change.
 */
(function () {
  'use strict';

  const CATALOGUE_URL = 'quiz/catalogue.json';
  const app = document.getElementById('app');
  const crumbs = document.getElementById('crumbs');

  /** @type {{matieres: Array<object>}|null} Catalogue, loaded once. */
  let catalogue = null;
  /** @type {Object<string, object>} Quiz files already downloaded, by URL. */
  const quizCache = {};

  // ------------------------------------------------------------- helpers

  /**
   * Escape a plain-text value before inserting it into HTML.
   * @param {*} text Value to escape.
   * @returns {string} HTML-safe text.
   */
  function esc(text) {
    return String(text).replace(/[&<>"']/g, ch => (
      { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]
    ));
  }

  /**
   * Download and parse a JSON file of the site.
   * @param {string} url Path relative to index.html.
   * @returns {Promise<object>} Parsed content.
   */
  async function loadJson(url) {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`${url} : erreur ${response.status}`);
    return response.json();
  }

  /**
   * Fisher-Yates shuffle, in place.
   * @param {Array} a Array to shuffle.
   * @returns {Array} The same array.
   */
  function shuffle(a) {
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
  }

  /**
   * Read the best score stored in this browser for a quiz.
   * @param {string} key Quiz key, "<subject>/<topic>".
   * @returns {{score: number, total: number}|null} Best score, if any.
   */
  function readBest(key) {
    try {
      const best = JSON.parse(localStorage.getItem('revisions:best:' + key));
      return best && typeof best.score === 'number' ? best : null;
    } catch (e) {
      return null; // storage unavailable or unreadable: the site works without it
    }
  }

  /**
   * Store a full-quiz score if it beats the previous best.
   * @param {string} key Quiz key, "<subject>/<topic>".
   * @param {number} score Number of correct answers.
   * @param {number} total Number of questions.
   */
  function saveBest(key, score, total) {
    const best = readBest(key);
    if (best && best.total === total && best.score >= score) return;
    try {
      localStorage.setItem('revisions:best:' + key, JSON.stringify({ score, total }));
    } catch (e) { /* private mode or full storage: ignore */ }
  }

  /**
   * Draw the breadcrumb.
   * @param {Array<{label: string, href: (string|undefined)}>} items Trail after the site name.
   */
  function setCrumbs(items) {
    crumbs.innerHTML = items.map(item => {
      const label = item.href
        ? `<a href="${esc(item.href)}">${esc(item.label)}</a>`
        : `<span aria-current="page">${esc(item.label)}</span>`;
      return `<span aria-hidden="true">›</span>${label}`;
    }).join('');
  }

  /**
   * Set the page title and move keyboard focus to the main heading of the new view.
   * @param {string} title Title of the view.
   */
  function finishView(title) {
    document.title = title === 'Révisions' ? title : `${title} · Révisions`;
    const heading = app.querySelector('h1');
    if (heading && viewsShown > 0) heading.focus();
    viewsShown += 1;
    window.scrollTo(0, 0);
  }
  let viewsShown = 0; // focus is only moved after the first view, not on page load

  /**
   * Show an error or "not found" message with a link back to the home page.
   * @param {string} title Short heading.
   * @param {string} message Explanation.
   */
  function viewMessage(title, message) {
    setCrumbs([]);
    app.innerHTML = `
      <div class="intro">
        <h1 tabindex="-1">${esc(title)}</h1>
        <p class="sub">${esc(message)}</p>
      </div>
      <p><a class="secondary" href="#/">Retour à l'accueil</a></p>`;
    finishView(title);
  }

  /**
   * French plural helper for the quiz count.
   * @param {number} n Number of quizzes.
   * @returns {string} "1 quiz", "3 quiz", or "Bientôt" when there is none.
   */
  function quizCount(n) {
    return n === 0 ? 'Bientôt' : `${n} quiz`;
  }

  // ------------------------------------------------------------- views

  /** Home page: one tile per subject. */
  function viewHome() {
    setCrumbs([]);
    const tiles = catalogue.matieres.map(m => {
      const n = m.themes.length;
      const series = (m.exercices || []).length;
      const meta = n || !series ? quizCount(n) : `${series} série${series > 1 ? 's' : ''} d'exercices`;
      const inner = `
        <span class="tile-title">${esc(m.titre)}</span>
        <span class="tile-meta">${meta}</span>`;
      return n || series
        ? `<li><a class="tile" href="#/${esc(m.id)}">${inner}</a></li>`
        : `<li><div class="tile empty">${inner}</div></li>`;
    }).join('');
    app.innerHTML = `
      <div class="intro">
        <h1 tabindex="-1">Choisis une matière</h1>
        <p class="sub">Des quiz pour réviser, avec la correction expliquée après chaque question.</p>
      </div>
      <ul class="list">${tiles}</ul>`;
    finishView('Révisions');
  }

  /**
   * Subject page: one tile per topic, then one tile per exercise series (PDF) when the subject has any.
   * @param {object} matiere Subject entry of the catalogue.
   */
  function viewSubject(matiere) {
    setCrumbs([{ label: matiere.titre }]);
    const tiles = matiere.themes.map(t => {
      const best = readBest(`${matiere.id}/${t.id}`);
      return `
        <li><a class="tile" href="#/${esc(matiere.id)}/${esc(t.id)}">
          <span class="tile-title">${esc(t.titre)}</span>
          ${t.description ? `<span class="tile-desc">${esc(t.description)}</span>` : ''}
          <span class="tile-meta">
            ${t.niveau ? `<span class="tag">${esc(t.niveau)}</span>` : ''}
            ${t.questions ? `<span>${esc(t.questions)} questions</span>` : ''}
            ${best ? `<span>Meilleur score : ${best.score} / ${best.total}</span>` : ''}
          </span>
        </a></li>`;
    }).join('');
    const series = (matiere.exercices || []).map(e => `
        <li><a class="tile" href="${esc(e.fichier)}">
          <span class="tile-title">${esc(e.titre)}</span>
          ${e.description ? `<span class="tile-desc">${esc(e.description)}</span>` : ''}
          <span class="tile-meta">
            ${e.niveau ? `<span class="tag">${esc(e.niveau)}</span>` : ''}
            <span>PDF avec corrigés</span>
          </span>
        </a></li>`).join('');
    app.innerHTML = `
      <div class="intro">
        <h1 tabindex="-1">${esc(matiere.titre)}</h1>
        <p class="sub">${matiere.themes.length ? 'Choisis un thème.' : 'Pas encore de quiz dans cette matière.'}</p>
      </div>
      <ul class="list">${tiles}</ul>
      ${series ? `
      <section class="section" aria-labelledby="exercices-title">
        <div class="intro">
          <h2 class="section-title" id="exercices-title">Exercices</h2>
          <p class="sub">Des séries d'exercices type bac avec leurs corrigés, à imprimer.</p>
        </div>
        <ul class="list">${series}</ul>
      </section>` : ''}`;
    finishView(matiere.titre);
  }

  /**
   * Quiz page. Runs the questions one at a time, then shows the results.
   *
   * In the quiz file, the FIRST entry of "reponses" is the correct answer;
   * answers are shuffled before being displayed. Question, answer, hint and
   * explanation texts may contain simple HTML such as <sub> and <sup>.
   *
   * @param {object} matiere Subject entry of the catalogue.
   * @param {object} theme Topic entry of the catalogue.
   * @param {object} quiz Content of the quiz file.
   */
  function viewQuiz(matiere, theme, quiz) {
    const questions = quiz.questions;
    const key = `${matiere.id}/${theme.id}`;
    const subjectHref = `#/${matiere.id}`;

    let order = [];     // indices of the questions in the current run
    let pos = 0;        // position in `order`
    let answers = {};   // question index -> chosen answer index (0 is the correct one)
    let layout = {};    // question index -> shuffled display order of its answers
    let fullRun = true; // false when only the missed questions are replayed

    setCrumbs([{ label: matiere.titre, href: subjectHref }, { label: theme.titre }]);
    app.innerHTML = `
      <div class="intro">
        <h1 tabindex="-1">${esc(quiz.titre || theme.titre)}</h1>
        <p class="sub">${quiz.niveau ? esc(quiz.niveau) + '. ' : ''}${questions.length} questions, une seule bonne réponse à chaque fois.</p>
      </div>
      <ol class="pips" id="pips" aria-label="Avancement du quiz"></ol>
      <div id="stage"></div>`;
    const pipsEl = document.getElementById('pips');
    const stage = document.getElementById('stage');

    /**
     * Start a run over the given question indices.
     * @param {number[]} indices Questions to ask.
     * @param {boolean} full True when the run covers the whole quiz.
     */
    function start(indices, full) {
      order = indices.slice();
      pos = 0;
      answers = {};
      layout = {};
      fullRun = full;
      order.forEach(qi => { layout[qi] = shuffle(questions[qi].reponses.map((_, i) => i)); });
      showQuestion(false);
    }

    /** Redraw the progress pips from the current state. */
    function drawPips() {
      pipsEl.innerHTML = order.map((qi, k) => {
        const a = answers[qi];
        let cls = 'pip';
        let label = 'à venir';
        if (a !== undefined) {
          cls += a === 0 ? ' ok' : ' ko';
          label = a === 0 ? 'réussie' : 'manquée';
        } else if (k === pos) {
          cls += ' now';
          label = 'en cours';
        }
        return `<li class="${cls}"><span class="sr">Question ${k + 1} : ${label}</span></li>`;
      }).join('');
    }

    /**
     * Display the current question.
     * @param {boolean} moveFocus Move keyboard focus to the question text.
     */
    function showQuestion(moveFocus) {
      const qi = order[pos];
      const q = questions[qi];
      drawPips();
      const options = layout[qi].map((oi, k) => `
        <li><button type="button" class="opt" data-oi="${oi}">
          <span class="letter" aria-hidden="true">${'ABCDEFGH'[k]}</span>
          <span class="txt">${q.reponses[oi]}</span>
          <span class="verdict"></span>
        </button></li>`).join('');
      const hint = q.indice ? `
        <button type="button" class="link" id="hintBtn">Voir un indice</button>
        <p class="hint" id="hint" hidden>${q.indice}</p>` : '';
      stage.innerHTML = `
        <article class="card">
          <p class="meta">
            <span>Question ${pos + 1} sur ${order.length}</span>
            ${q.categorie ? `<span class="tag">${esc(q.categorie)}</span>` : ''}
          </p>
          <h2 id="prompt" tabindex="-1">${q.question}</h2>
          <ol class="options" aria-labelledby="prompt">${options}</ol>
          ${hint}
          <div id="feedback" class="feedback" hidden></div>
        </article>`;

      stage.querySelectorAll('.opt').forEach(button => {
        button.addEventListener('click', () => answer(Number(button.dataset.oi)));
      });
      const hintBtn = document.getElementById('hintBtn');
      if (hintBtn) {
        hintBtn.addEventListener('click', () => {
          document.getElementById('hint').hidden = false;
          hintBtn.hidden = true;
        });
      }
      if (moveFocus) document.getElementById('prompt').focus();
    }

    /**
     * Record the chosen answer, lock the question and show the explanation.
     * @param {number} oi Index of the chosen answer in "reponses".
     */
    function answer(oi) {
      const qi = order[pos];
      const q = questions[qi];
      if (answers[qi] !== undefined) return;
      answers[qi] = oi;
      const right = oi === 0;

      stage.querySelectorAll('.opt').forEach(button => {
        const o = Number(button.dataset.oi);
        button.disabled = true;
        if (o === 0) {
          button.classList.add('is-right');
          button.querySelector('.verdict').textContent = 'Bonne réponse';
        } else if (o === oi) {
          button.classList.add('is-wrong');
          button.querySelector('.verdict').textContent = 'Ta réponse';
        } else {
          button.classList.add('is-dim');
        }
      });
      const hintBtn = document.getElementById('hintBtn');
      if (hintBtn) hintBtn.hidden = true;

      const last = pos === order.length - 1;
      const feedback = document.getElementById('feedback');
      feedback.className = 'feedback ' + (right ? 'good' : 'bad');
      feedback.innerHTML = `
        <p class="fb-title">${right ? 'Juste.' : 'Pas tout à fait.'}</p>
        <p>${q.explication || ''}</p>
        <button type="button" class="primary" id="nextBtn">${last ? 'Voir mon résultat' : 'Question suivante'}</button>`;
      feedback.hidden = false;
      drawPips();

      const nextBtn = document.getElementById('nextBtn');
      nextBtn.addEventListener('click', () => {
        if (last) {
          showResults();
        } else {
          pos += 1;
          showQuestion(true);
        }
      });
      nextBtn.focus({ preventScroll: true });
    }

    /** Display the score, the split by category and the questions to review. */
    function showResults() {
      pos = order.length;
      drawPips();
      const total = order.length;
      const isRight = qi => answers[qi] === 0;
      const score = order.filter(isRight).length;
      const missed = order.filter(qi => !isRight(qi));
      const ratio = score / total;
      if (fullRun) saveBest(key, score, total);

      let comment;
      if (ratio === 1) comment = 'Sans faute. Le chapitre est maîtrisé.';
      else if (ratio >= 0.8) comment = 'Très solide. Il reste quelques points à revoir ci-dessous.';
      else if (ratio >= 0.5) comment = 'Les bases sont là. Relis les corrections ci-dessous, puis refais ces questions.';
      else comment = 'Ce chapitre demande encore du travail. Relis les corrections ci-dessous, puis recommence.';

      // Score per category, in order of first appearance
      const categories = [];
      order.forEach(qi => {
        const c = questions[qi].categorie;
        if (c && !categories.includes(c)) categories.push(c);
      });
      const split = categories.length > 1 ? categories.map(c => {
        const qs = order.filter(qi => questions[qi].categorie === c);
        return `<li><span>${esc(c)}</span><strong>${qs.filter(isRight).length} / ${qs.length}</strong></li>`;
      }).join('') : '';

      const review = missed.length ? `
        <section class="review">
          <h3>${missed.length === 1 ? 'La question à revoir' : `Les ${missed.length} questions à revoir`}</h3>
          ${missed.map(qi => {
            const q = questions[qi];
            return `<div class="missed">
              <p class="mq">${q.question}</p>
              <p class="yours">Ta réponse : ${q.reponses[answers[qi]]}</p>
              <p class="right">Bonne réponse : ${q.reponses[0]}</p>
              <p class="why">${q.explication || ''}</p>
            </div>`;
          }).join('')}
        </section>` : '';

      const all = questions.length;
      stage.innerHTML = `
        <article class="card">
          <h2 id="resultTitle" tabindex="-1">Ton résultat</h2>
          <p class="score">${score}<small> / ${total}</small></p>
          <p class="comment">${comment}</p>
          ${split ? `<ul class="split">${split}</ul>` : ''}
          <div class="actions">
            ${missed.length ? `<button type="button" class="primary" id="retryBtn">Refaire ${missed.length === 1 ? 'la question manquée' : `les ${missed.length} questions manquées`}</button>` : ''}
            <button type="button" class="${missed.length ? 'secondary' : 'primary'}" id="restartBtn">Recommencer les ${all} questions</button>
            <a class="secondary" href="${esc(subjectHref)}">Choisir un autre thème</a>
          </div>
          ${review}
        </article>`;

      const retryBtn = document.getElementById('retryBtn');
      if (retryBtn) {
        retryBtn.addEventListener('click', () => {
          start(missed, false);
          document.getElementById('prompt').focus();
        });
      }
      document.getElementById('restartBtn').addEventListener('click', () => {
        start(questions.map((_, i) => i), true);
        document.getElementById('prompt').focus();
      });
      document.getElementById('resultTitle').focus();
      window.scrollTo(0, 0);
    }

    start(questions.map((_, i) => i), true);
    finishView(quiz.titre || theme.titre);
  }

  // ------------------------------------------------------------- router

  /** Read the URL hash and display the matching view. */
  async function route() {
    const parts = location.hash.replace(/^#\/?/, '').split('/').filter(Boolean).map(decodeURIComponent);
    try {
      if (!catalogue) catalogue = await loadJson(CATALOGUE_URL);
      if (parts.length === 0) return viewHome();

      const matiere = catalogue.matieres.find(m => m.id === parts[0]);
      if (!matiere) return viewMessage('Page introuvable', "Cette matière n'existe pas.");
      if (parts.length === 1) return viewSubject(matiere);

      const theme = matiere.themes.find(t => t.id === parts[1]);
      if (!theme) return viewMessage('Page introuvable', "Ce quiz n'existe pas ou a été déplacé.");
      if (!quizCache[theme.fichier]) quizCache[theme.fichier] = await loadJson(theme.fichier);
      return viewQuiz(matiere, theme, quizCache[theme.fichier]);
    } catch (error) {
      console.error(error);
      return viewMessage('Chargement impossible', 'Vérifie ta connexion, puis recharge la page.');
    }
  }

  window.addEventListener('hashchange', route);
  route();
})();
