/**
 * Trainingsgids <-> Google Sheet sync.
 *
 * Paste this file into the Google Sheet via Extensions > Apps Script.
 * 1. Run setup() once and copy the code it logs.
 * 2. Deploy > New deployment > Web app, execute as "Me", access "Anyone".
 *    After changing this file: Deploy > Manage deployments > edit > New version.
 * 3. Enter the web app URL and the code in the guide (Instellingen > Sync instellen).
 *
 * The guide posts its logbook, weights and weekly notes; this script writes
 * them into the training and weight tabs and sends back the overview tabs so
 * the guide can show them. It also keeps a full copy of the logbook (one row
 * per set) in the tab "App-logboek", so a new install of the guide can get
 * its logbook back (action "restore"). An iOS Shortcut can post the daily
 * step count. Every request needs the secret code from the script properties.
 */

var TRAINING_SHEET = 'Trainingsschema & Logboek';
var WEIGHT_SHEET = 'Gewicht & Metingen';
var OVERVIEW_SHEET = 'Overzicht & Voeding';
var LOG_SHEET = 'App-logboek';
var LOG_HEAD = ['Soort', 'Datum', 'Oefening', 'Set', 'Kg', 'Reps', 'Tekst'];
var MONTHS = ['jan', 'feb', 'mrt', 'apr', 'mei', 'jun', 'jul', 'aug', 'sep', 'okt', 'nov', 'dec'];
var DAY_HEADERS = ['Ma (kg)', 'Di (kg)', 'Wo (kg)', 'Do (kg)', 'Vr (kg)', 'Za (kg)', 'Zo (kg)'];

// Exercise ids per training day, in the order of the sheet's # column.
var DAYS = [
  ['incline-press', 'one-arm-row', 'flat-press', 'cs-row', 'lateral-raise', 'incline-curl'],
  ['bulgarian', 'goblet', 'rdl', 'calf', 'situp'],
  ['shoulder-press', 'pullover', 'incline-fly', 'rear-delt', 'tricep-ext', 'hammer'],
  ['rdl-heavy', 'reverse-lunge', 'glute-bridge', 'single-calf', 'russian-twist']
];
// Planned weekday per training day (0 = Monday): Tue, Thu, Fri, Sun.
var PLANNED = [1, 3, 4, 6];
// A training up to this many days after its planned day still counts for
// that week, also when it falls in the next calendar week (Sunday -> Monday).
var LATE_DAYS = 3;

/** Run once from the editor: creates the secret code and logs it. */
function setup() {
  var props = PropertiesService.getScriptProperties();
  var token = props.getProperty('TOKEN');
  if (!token) {
    token = Utilities.getUuid().replace(/-/g, '').slice(0, 16);
    props.setProperty('TOKEN', token);
  }
  Logger.log('Code voor de trainingsgids: ' + token);
  return token;
}

/**
 * Run once from the editor to start fresh: clears the example data in
 * Week 1 and Week 2 (training: weight/reps; weights tab: daily weights,
 * waist, steps and notes; formulas stay) and makes the current week Week 1.
 * Afterwards tap "Sync naar sheet" in the guide to write your data again.
 */
function startOpnieuwInWeek1() {
  var ss = SpreadsheetApp.getActive();
  var props = PropertiesService.getScriptProperties();
  var weeks = [1, 2];

  var tSheet = sheet_(ss, TRAINING_SHEET);
  var tLay = trainingLayout_(tSheet.getDataRange().getDisplayValues());
  weeks.forEach(function (w) {
    var cols = tLay.weeks[w];
    if (!cols) { return; }
    Object.keys(tLay.rows).forEach(function (id) {
      tSheet.getRange(tLay.rows[id], cols.kg, 1, 2).clearContent();
    });
  });

  var wSheet = sheet_(ss, WEIGHT_SHEET);
  var wValues = wSheet.getDataRange().getDisplayValues();
  var wLay = weightLayout_(wValues);
  var head = wValues.filter(function (r) { return r.indexOf(DAY_HEADERS[0]) >= 0; })[0];
  var waist = head ? head.map(function (v) { return String(v).trim(); }).indexOf('Taille (cm)') + 1 : 0;
  weeks.forEach(function (w) {
    var row = wLay.rows[w];
    if (!row) { return; }
    wLay.days.concat([waist, wLay.steps, wLay.notes]).forEach(function (c) {
      if (c) { wSheet.getRange(row, c).clearContent(); }
    });
    if (wLay.range) { wSheet.getRange(row, wLay.range).setValue('Week ' + w); }
  });

  var now = new Date();
  var today = Utilities.formatDate(now, Session.getScriptTimeZone(), 'yyyy-MM-dd');
  var anchor = { monday: iso_(monday_(today)), week: 1 };
  props.setProperty('ANCHOR', JSON.stringify(anchor));
  Logger.log('Klaar. Week van ' + anchor.monday + ' is nu Week 1. Tik in de gids op "Sync naar sheet".');
  return anchor;
}

function doGet() {
  return json_({ ok: true, app: 'trainingsgids' });
}

function doPost(e) {
  var lock = LockService.getScriptLock();
  try {
    lock.waitLock(20000);
    var body = JSON.parse(e.postData.contents);
    var props = PropertiesService.getScriptProperties();
    if (!props.getProperty('TOKEN') || String(body.token).trim() !== props.getProperty('TOKEN')) {
      return json_({ ok: false, error: 'Ongeldige code' });
    }
    var ss = SpreadsheetApp.getActive();
    if (body.action === 'steps') {
      return json_(steps_(ss, props, body));
    }
    if (body.action === 'restore') {
      return json_(restore_(ss, props));
    }
    return json_(sync_(ss, props, body));
  } catch (err) {
    return json_({ ok: false, error: String(err && err.message || err) });
  } finally {
    lock.releaseLock();
  }
}

function json_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}

function sheet_(ss, name) {
  var sh = ss.getSheetByName(name);
  if (!sh) { throw new Error('Tabblad "' + name + '" niet gevonden'); }
  return sh;
}

// ---------- dates and weeks ----------
function parseDate_(iso) {
  var p = String(iso).split('-');
  return new Date(Date.UTC(+p[0], +p[1] - 1, +p[2]));
}

function monday_(iso) {
  var d = parseDate_(iso);
  d.setUTCDate(d.getUTCDate() - (d.getUTCDay() + 6) % 7);
  return d;
}

function iso_(d) {
  return d.toISOString().slice(0, 10);
}

function isIso_(s) {
  return /^\d{4}-\d{2}-\d{2}$/.test(String(s));
}

/**
 * Week anchor shared by all tabs: the first synced week goes to the first
 * Week column of the training tab that is still empty.
 */
function anchor_(props, ss, firstDate) {
  var saved = props.getProperty('ANCHOR');
  if (saved) { return JSON.parse(saved); }
  if (!firstDate) { return null; }
  var values = sheet_(ss, TRAINING_SHEET).getDataRange().getDisplayValues();
  var lay = trainingLayout_(values);
  var weekNums = Object.keys(lay.weeks).map(Number).sort(function (a, b) { return a - b; });
  var lastFilled = 0;
  weekNums.forEach(function (w) {
    Object.keys(lay.rows).forEach(function (id) {
      var r = lay.rows[id] - 1;
      if (values[r][lay.weeks[w].kg - 1] || values[r][lay.weeks[w].reps - 1]) { lastFilled = Math.max(lastFilled, w); }
    });
  });
  var week = weekNums.filter(function (w) { return w > lastFilled; })[0];
  if (!week) { throw new Error('Alle Week-kolommen zijn al gevuld'); }
  var anchor = { monday: iso_(monday_(firstDate)), week: week };
  props.setProperty('ANCHOR', JSON.stringify(anchor));
  return anchor;
}

function weekOf_(anchor, iso) {
  return anchor.week + Math.round((monday_(iso).getTime() - parseDate_(anchor.monday).getTime()) / (7 * 864e5));
}

// ---------- training tab ----------
function trainingLayout_(values) {
  var weeks = {};
  var dayRows = [];
  for (var r = 0; r < values.length; r++) {
    for (var c = 0; c < values[r].length; c++) {
      var m = /^Week (\d+)$/.exec(String(values[r][c]).trim());
      if (m && !weeks[m[1]]) { weeks[m[1]] = { kg: c + 1, reps: c + 2 }; }
    }
    if (/^DAG \d/.test(String(values[r][1]).trim())) { dayRows.push(r); }
  }
  if (dayRows.length !== DAYS.length) { throw new Error('Kon de dagen in het trainingsschema niet vinden'); }
  var rows = {};
  DAYS.forEach(function (ids, d) {
    ids.forEach(function (id, i) {
      for (var r = dayRows[d] + 1; r < Math.min(values.length, dayRows[d] + 12); r++) {
        if (String(values[r][1]).trim().replace(/\.0$/, '') === String(i + 1)) { rows[id] = r + 1; break; }
      }
      if (!rows[id]) { throw new Error('Rij voor ' + id + ' niet gevonden'); }
    });
  });
  return { weeks: weeks, rows: rows };
}

function describe_(sets) {
  var kgs = sets.map(function (s) { return String(s.kg || '').replace('.', ','); });
  var reps = sets.map(function (s) { return s.reps || '?'; }).join(', ');
  var weight;
  if (kgs.every(function (k) { return !k; })) {
    weight = 'Lichaam';
  } else if (kgs.every(function (k) { return k === kgs[0]; })) {
    weight = kgs[0] + ' kg';
  } else {
    weight = kgs.map(function (k) { return k || '–'; }).join(' / ') + ' kg';
  }
  return { weight: weight, reps: reps };
}

function plannedDay_(id) {
  for (var d = 0; d < DAYS.length; d++) {
    if (DAYS[d].indexOf(id) >= 0) { return PLANNED[d]; }
  }
  return -1;
}

/**
 * Assigns each training to a week: normally its calendar week (Mon-Sun).
 * A training done at most LATE_DAYS after its planned day, but already in
 * the next calendar week, goes to the previous week when that week has no
 * training of this exercise yet. Per exercise and week the latest wins.
 * Returns { 'id|week': { id, week, date, sets, natural } }.
 */
function assignWeeks_(entries, anchor, lay) {
  var byId = {};
  entries.forEach(function (e) {
    if (!lay.rows[e.id] || !isIso_(e.date) || !e.sets || !e.sets.length) { return; }
    (byId[e.id] = byId[e.id] || []).push(e);
  });
  var latest = {};
  Object.keys(byId).forEach(function (id) {
    var planned = plannedDay_(id);
    byId[id].sort(function (a, b) { return a.date < b.date ? -1 : a.date > b.date ? 1 : 0; });
    byId[id].forEach(function (e) {
      var natural = weekOf_(anchor, e.date);
      var w = natural;
      var prev = natural - 1;
      var plannedPrev = monday_(e.date).getTime() + (planned - 7) * 864e5;
      var late = Math.round((parseDate_(e.date).getTime() - plannedPrev) / 864e5);
      if (planned >= 0 && late <= LATE_DAYS && prev >= anchor.week && lay.weeks[prev] && !latest[id + '|' + prev]) {
        w = prev;
      }
      latest[id + '|' + w] = { id: id, week: w, date: e.date, sets: e.sets, natural: natural };
    });
  });
  return latest;
}

function syncTraining_(sheet, entries, anchor, out) {
  var values = sheet.getDataRange().getDisplayValues();
  var lay = trainingLayout_(values);
  var latest = assignWeeks_(entries, anchor, lay);
  // A training that moved to the previous week may still be in its calendar
  // week from an earlier sync: clear it there if nothing else belongs there.
  Object.keys(latest).forEach(function (key) {
    var s = latest[key];
    var cols = lay.weeks[s.natural];
    if (s.week === s.natural || !cols || latest[s.id + '|' + s.natural]) { return; }
    var row = lay.rows[s.id];
    var d = describe_(s.sets);
    if (values[row - 1][cols.kg - 1] === d.weight && values[row - 1][cols.reps - 1] === d.reps) {
      sheet.getRange(row, cols.kg, 1, 2).clearContent();
      values[row - 1][cols.kg - 1] = '';
      values[row - 1][cols.reps - 1] = '';
      out.changed += 2;
      addWeek_(out, s.natural);
    }
  });
  Object.keys(latest).forEach(function (key) {
    var s = latest[key];
    var cols = lay.weeks[s.week];
    if (!cols) { out.skipped.push(s.id + ' (' + s.date + ', week ' + s.week + ')'); return; }
    var row = lay.rows[s.id];
    var d = describe_(s.sets);
    [[cols.kg, d.weight], [cols.reps, d.reps]].forEach(function (cell) {
      if (values[row - 1][cell[0] - 1] !== cell[1]) {
        sheet.getRange(row, cell[0]).setNumberFormat('@').setValue(cell[1]);
        out.changed++;
        addWeek_(out, s.week);
      }
    });
  });
}

// ---------- weight tab ----------
function weightLayout_(values) {
  var head = -1;
  for (var r = 0; r < values.length && head < 0; r++) {
    if (values[r].indexOf(DAY_HEADERS[0]) >= 0) { head = r; }
  }
  if (head < 0) { throw new Error('Kon de weegtabel niet vinden'); }
  var h = values[head].map(function (v) { return String(v).trim(); });
  var col = function (pred) {
    for (var c = 0; c < h.length; c++) { if (pred(h[c])) { return c + 1; } }
    return 0;
  };
  var lay = {
    days: DAY_HEADERS.map(function (d) { return col(function (v) { return v === d; }); }),
    range: col(function (v) { return v === 'Datumbereik'; }),
    steps: col(function (v) { return /stappen/i.test(v); }),
    notes: col(function (v) { return /^opmerkingen/i.test(v); }),
    rows: {}
  };
  for (var r2 = head + 1; r2 < values.length; r2++) {
    var m = /^Week (\d+)$/.exec(String(values[r2][1]).trim());
    if (m) { lay.rows[m[1]] = r2 + 1; }
  }
  return lay;
}

function rangeLabel_(mondayIso) {
  var a = parseDate_(mondayIso);
  var b = new Date(a.getTime() + 6 * 864e5);
  return a.getUTCDate() + ' ' + MONTHS[a.getUTCMonth()] + ' – ' + b.getUTCDate() + ' ' + MONTHS[b.getUTCMonth()];
}

function labelWeek_(sheet, values, lay, row, week, anchor) {
  if (!lay.range) { return; }
  var cur = String(values[row - 1][lay.range - 1]).trim();
  if (cur === '' || cur === 'Week ' + week) {
    var mon = new Date(parseDate_(anchor.monday).getTime() + (week - anchor.week) * 7 * 864e5);
    var label = rangeLabel_(iso_(mon));
    sheet.getRange(row, lay.range).setValue(label);
    values[row - 1][lay.range - 1] = label;
  }
}

function syncWeights_(sheet, weights, notes, anchor, out) {
  var values = sheet.getDataRange().getDisplayValues();
  var lay = weightLayout_(values);
  Object.keys(weights || {}).forEach(function (date) {
    if (!isIso_(date)) { return; }
    var w = weekOf_(anchor, date);
    var row = lay.rows[w];
    if (!row) { out.skipped.push('gewicht ' + date + ' (week ' + w + ')'); return; }
    var dayCol = lay.days[(parseDate_(date).getUTCDay() + 6) % 7];
    var kg = weights[date];
    var cur = String(values[row - 1][dayCol - 1]).trim().replace(',', '.');
    if (kg === null || kg === '') {
      if (cur !== '') { sheet.getRange(row, dayCol).clearContent(); out.changed++; addWeek_(out, w); }
      return;
    }
    var num = Number(String(kg).replace(',', '.'));
    if (!isFinite(num)) { return; }
    if (Number(cur) !== num || cur === '') {
      sheet.getRange(row, dayCol).setValue(num);
      out.changed++;
      addWeek_(out, w);
      labelWeek_(sheet, values, lay, row, w, anchor);
    }
  });
  Object.keys(notes || {}).forEach(function (mon) {
    if (!isIso_(mon) || !lay.notes) { return; }
    var w = weekOf_(anchor, mon);
    var row = lay.rows[w];
    if (!row) { out.skipped.push('notitie week ' + w); return; }
    var text = String(notes[mon] || '');
    if (String(values[row - 1][lay.notes - 1]) !== text) {
      sheet.getRange(row, lay.notes).setValue(text);
      out.changed++;
      addWeek_(out, w);
    }
  });
}

/** Daily step count from an iOS Shortcut: { action: 'steps', date, steps }. */
function steps_(ss, props, body) {
  var date = isIso_(body.date) ? body.date : iso_(new Date());
  var steps = Math.round(Number(String(body.steps).replace(',', '.')));
  if (!isFinite(steps) || steps < 0) { return { ok: false, error: 'Ongeldig aantal stappen' }; }
  var all = JSON.parse(props.getProperty('STEPS') || '{}');
  all[date] = steps;
  props.setProperty('STEPS', JSON.stringify(all));
  var anchor = anchor_(props, ss, date);
  var sheet = sheet_(ss, WEIGHT_SHEET);
  var values = sheet.getDataRange().getDisplayValues();
  var lay = weightLayout_(values);
  var w = weekOf_(anchor, date);
  var row = lay.rows[w];
  if (!row || !lay.steps) { return { ok: true, stored: true, week: w, message: 'Week ' + w + ' staat niet in de sheet' }; }
  var mon = monday_(date).getTime();
  var days = Object.keys(all).filter(function (d) {
    var t = parseDate_(d).getTime();
    return t >= mon && t < mon + 7 * 864e5;
  });
  var avg = Math.round(days.reduce(function (s, d) { return s + all[d]; }, 0) / days.length);
  sheet.getRange(row, lay.steps).setValue(avg);
  labelWeek_(sheet, values, lay, row, w, anchor);
  return { ok: true, week: w, days: days.length, average: avg };
}

// ---------- overview for the guide ----------
/** Splits a tab into blocks of non-empty rows, dropping empty columns. */
function blocks_(sheet) {
  var values = sheet.getDataRange().getDisplayValues();
  var blocks = [];
  var cur = [];
  var flush = function () {
    if (!cur.length) { return; }
    var used = [];
    cur.forEach(function (row) {
      row.forEach(function (v, c) { if (String(v).trim() !== '' && used.indexOf(c) < 0) { used.push(c); } });
    });
    used.sort(function (a, b) { return a - b; });
    var rows = cur.map(function (row) { return used.map(function (c) { return String(row[c]).trim(); }); });
    var title = '';
    var first = rows[0].filter(function (v) { return v !== ''; });
    if (first.length === 1 && rows.length > 1) {
      title = first[0];
      rows.shift();
    }
    blocks.push({ title: title, rows: rows });
    cur = [];
  };
  values.forEach(function (row) {
    if (row.every(function (v) { return String(v).trim() === ''; })) { flush(); } else { cur.push(row); }
  });
  flush();
  return blocks;
}

function addWeek_(out, w) {
  if (out.weeks.indexOf(w) < 0) { out.weeks.push(w); }
}

function sync_(ss, props, body) {
  var entries = body.entries || [];
  var weights = body.weights || {};
  var notes = body.notes || {};
  var dates = entries.map(function (e) { return e.date; })
    .concat(Object.keys(weights), Object.keys(notes)).filter(isIso_).sort();
  var out = { ok: true, changed: 0, weeks: [], skipped: [] };
  var anchor = anchor_(props, ss, dates[0]);
  if (anchor) {
    syncTraining_(sheet_(ss, TRAINING_SHEET), entries, anchor, out);
    syncWeights_(sheet_(ss, WEIGHT_SHEET), weights, notes, anchor, out);
  }
  saveLog_(ss, entries, weights, notes);
  SpreadsheetApp.flush();
  out.anchor = anchor;
  out.weeks.sort(function (a, b) { return a - b; });
  out.overview = {
    voeding: ss.getSheetByName(OVERVIEW_SHEET) ? blocks_(ss.getSheetByName(OVERVIEW_SHEET)) : [],
    metingen: blocks_(sheet_(ss, WEIGHT_SHEET))
  };
  out.steps = JSON.parse(props.getProperty('STEPS') || '{}');
  return out;
}

// ---------- full logbook copy (tab "App-logboek") ----------
function cellDate_(v) {
  if (v instanceof Date) { return Utilities.formatDate(v, Session.getScriptTimeZone(), 'yyyy-MM-dd'); }
  return String(v).trim();
}

/** Reads the App-logboek tab: { sets: {'date|id': [{n, kg, reps}]}, weights: {date: kg}, notes: {monday: text} }. */
function readLog_(ss) {
  var log = { sets: {}, weights: {}, notes: {} };
  var sh = ss.getSheetByName(LOG_SHEET);
  if (!sh || sh.getLastRow() < 2) { return log; }
  sh.getRange(2, 1, sh.getLastRow() - 1, LOG_HEAD.length).getValues().forEach(function (r) {
    var kind = String(r[0]).trim(), date = cellDate_(r[1]);
    if (!isIso_(date)) { return; }
    if (kind === 'set' && r[2]) {
      var key = date + '|' + String(r[2]).trim();
      (log.sets[key] = log.sets[key] || []).push({ n: Number(r[3]) || 0, kg: String(r[4]).trim(), reps: String(r[5]).trim() });
    } else if (kind === 'gewicht' && r[4] !== '') {
      log.weights[date] = Number(String(r[4]).replace(',', '.'));
    } else if (kind === 'notitie' && String(r[6]) !== '') {
      log.notes[date] = String(r[6]);
    }
  });
  return log;
}

/**
 * Merges the guide's data into the copy. A training (date + exercise) the
 * guide sends replaces the stored one; anything it does not send is kept, so
 * a new, still empty install cannot wipe the copy before it is restored.
 */
function saveLog_(ss, entries, weights, notes) {
  if (!entries.length && !Object.keys(weights).length && !Object.keys(notes).length) { return; }
  var log = readLog_(ss);
  entries.forEach(function (e) {
    if (!isIso_(e.date) || !e.id || !e.sets || !e.sets.length) { return; }
    log.sets[e.date + '|' + e.id] = e.sets.map(function (st, i) {
      return { n: Number(st.n) || i + 1, kg: String(st.kg || ''), reps: String(st.reps || '') };
    });
  });
  Object.keys(weights).forEach(function (d) {
    if (!isIso_(d)) { return; }
    if (weights[d] === null || weights[d] === '') { delete log.weights[d]; } else { log.weights[d] = Number(String(weights[d]).replace(',', '.')); }
  });
  Object.keys(notes).forEach(function (d) {
    if (!isIso_(d)) { return; }
    if (!notes[d]) { delete log.notes[d]; } else { log.notes[d] = String(notes[d]); }
  });
  var rows = [];
  Object.keys(log.sets).sort().forEach(function (key) {
    var k = key.split('|');
    log.sets[key].slice().sort(function (a, b) { return a.n - b.n; }).forEach(function (st) {
      rows.push(['set', k[0], k[1], st.n, st.kg, st.reps, '']);
    });
  });
  Object.keys(log.weights).sort().forEach(function (d) { rows.push(['gewicht', d, '', '', String(log.weights[d]), '', '']); });
  Object.keys(log.notes).sort().forEach(function (d) { rows.push(['notitie', d, '', '', '', '', log.notes[d]]); });

  var sh = ss.getSheetByName(LOG_SHEET) || ss.insertSheet(LOG_SHEET);
  sh.clearContents();
  var all = [LOG_HEAD].concat(rows);
  sh.getRange(1, 1, all.length, LOG_HEAD.length).setNumberFormat('@').setValues(all);
  sh.getRange(1, 1, 1, LOG_HEAD.length).setFontWeight('bold');
  sh.setFrozenRows(1);
}

/** Splits a Week cell ("22 kg", "22 / 20 kg", "Lichaam" and "10, 9, 8") back into sets. */
function parseWeek_(weight, reps) {
  var r = String(reps).split(',').map(function (x) { x = x.trim(); return x === '?' ? '' : x; });
  var w = String(weight).trim();
  var kgs = /kg$/.test(w) ? w.replace(/\s*kg$/, '').split('/').map(function (x) { x = x.trim(); return x === '–' ? '' : x.replace(',', '.'); }) : [''];
  return r.map(function (x, i) { return { n: i + 1, kg: kgs.length === 1 ? kgs[0] : (kgs[i] || ''), reps: x }; });
}

/**
 * Everything a new install needs: the App-logboek copy, plus older weeks
 * that are only in the Week columns and the weights tab (dated on the
 * planned day of that week).
 */
function restore_(ss, props) {
  var log = readLog_(ss);
  var saved = props.getProperty('ANCHOR');
  var anchor = saved ? JSON.parse(saved) : null;
  var fromWeeks = 0;
  if (anchor) {
    var dayOf = function (week, day) {
      return iso_(new Date(parseDate_(anchor.monday).getTime() + ((week - anchor.week) * 7 + day) * 864e5));
    };
    var have = {};
    Object.keys(log.sets).forEach(function (key) {
      var k = key.split('|');
      have[k[1] + '|' + weekOf_(anchor, k[0])] = true;
    });
    var values = sheet_(ss, TRAINING_SHEET).getDataRange().getDisplayValues();
    var lay = trainingLayout_(values);
    DAYS.forEach(function (ids, d) {
      ids.forEach(function (id) {
        Object.keys(lay.weeks).forEach(function (w) {
          var row = values[lay.rows[id] - 1], c = lay.weeks[w];
          var weight = row[c.kg - 1], reps = row[c.reps - 1];
          if (!String(reps).trim() || have[id + '|' + w]) { return; }
          log.sets[dayOf(Number(w), PLANNED[d]) + '|' + id] = parseWeek_(weight, reps);
          fromWeeks++;
        });
      });
    });
    var wValues = sheet_(ss, WEIGHT_SHEET).getDataRange().getDisplayValues();
    var wLay = weightLayout_(wValues);
    Object.keys(wLay.rows).forEach(function (w) {
      var row = wValues[wLay.rows[w] - 1];
      wLay.days.forEach(function (c, i) {
        var v = c ? String(row[c - 1]).trim().replace(',', '.') : '';
        var date = dayOf(Number(w), i);
        if (v !== '' && isFinite(Number(v)) && log.weights[date] === undefined) { log.weights[date] = Number(v); }
      });
      var note = wLay.notes ? String(row[wLay.notes - 1]).trim() : '';
      var mon = dayOf(Number(w), 0);
      if (note && log.notes[mon] === undefined) { log.notes[mon] = note; }
    });
  }
  var entries = Object.keys(log.sets).sort().map(function (key) {
    var k = key.split('|');
    return { date: k[0], id: k[1], sets: log.sets[key] };
  });
  return { ok: true, entries: entries, weights: log.weights, notes: log.notes, fromWeeks: fromWeeks };
}
