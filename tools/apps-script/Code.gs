/**
 * Trainingsgids -> Google Sheet sync.
 *
 * Paste this file into the Google Sheet via Extensions > Apps Script.
 * 1. Run setup() once and copy the code it logs.
 * 2. Deploy > New deployment > Web app, execute as "Me", access "Anyone".
 * 3. Enter the web app URL and the code in the guide (Logboek > Sync instellen).
 *
 * The guide posts its whole logbook. This script only writes the weight and
 * reps cells of the Week columns on the training tab; the code (a random
 * secret kept in the script properties) keeps others out.
 */

var SHEET_NAME = 'Trainingsschema & Logboek';

// Exercise ids per training day, in the order of the sheet's # column.
var DAYS = [
  ['incline-press', 'one-arm-row', 'flat-press', 'cs-row', 'lateral-raise', 'incline-curl'],
  ['bulgarian', 'goblet', 'rdl', 'calf', 'situp'],
  ['shoulder-press', 'pullover', 'incline-fly', 'rear-delt', 'tricep-ext', 'hammer'],
  ['rdl-heavy', 'reverse-lunge', 'hip-thrust', 'single-calf', 'russian-twist']
];

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

function doGet() {
  return json_({ ok: true, app: 'trainingsgids' });
}

function doPost(e) {
  var lock = LockService.getScriptLock();
  try {
    lock.waitLock(20000);
    var body = JSON.parse(e.postData.contents);
    var props = PropertiesService.getScriptProperties();
    if (!props.getProperty('TOKEN') || body.token !== props.getProperty('TOKEN')) {
      return json_({ ok: false, error: 'Ongeldige code' });
    }
    var sheet = SpreadsheetApp.getActive().getSheetByName(SHEET_NAME);
    if (!sheet) {
      return json_({ ok: false, error: 'Tabblad "' + SHEET_NAME + '" niet gevonden' });
    }
    return json_(sync_(sheet, body.entries || [], props, !!body.dryRun));
  } catch (err) {
    return json_({ ok: false, error: String(err) });
  } finally {
    lock.releaseLock();
  }
}

function json_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}

/** Finds the Week columns and the row of every exercise. Rows/cols are 1-based. */
function layout_(values) {
  var weeks = {};
  var dayRows = [];
  for (var r = 0; r < values.length; r++) {
    for (var c = 0; c < values[r].length; c++) {
      var m = /^Week (\d+)$/.exec(String(values[r][c]).trim());
      if (m && !weeks[m[1]]) { weeks[m[1]] = { kg: c + 1, reps: c + 2 }; }
    }
    if (/^DAG \d/.test(String(values[r][1]).trim())) { dayRows.push(r); }
  }
  if (dayRows.length !== DAYS.length) { throw new Error('Kon de dagen in de sheet niet vinden'); }
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

function monday_(iso) {
  var p = iso.split('-');
  var d = new Date(Date.UTC(+p[0], +p[1] - 1, +p[2]));
  var dow = (d.getUTCDay() + 6) % 7;
  d.setUTCDate(d.getUTCDate() - dow);
  return d;
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

function sync_(sheet, entries, props, dryRun) {
  var values = sheet.getDataRange().getDisplayValues();
  var lay = layout_(values);
  var weekNums = Object.keys(lay.weeks).map(Number).sort(function (a, b) { return a - b; });

  entries = entries.filter(function (e) {
    return lay.rows[e.id] && /^\d{4}-\d{2}-\d{2}$/.test(e.date) && e.sets && e.sets.length;
  });
  if (!entries.length) { return { ok: true, changed: 0, message: 'Geen afgeronde sets om te syncen' }; }

  // Week anchor: the first synced week goes to the first empty Week column.
  var anchor = props.getProperty('ANCHOR');
  if (anchor) {
    anchor = JSON.parse(anchor);
  } else {
    var lastFilled = 0;
    weekNums.forEach(function (w) {
      Object.keys(lay.rows).forEach(function (id) {
        var r = lay.rows[id] - 1;
        if (values[r][lay.weeks[w].kg - 1] || values[r][lay.weeks[w].reps - 1]) { lastFilled = Math.max(lastFilled, w); }
      });
    });
    var firstWeek = weekNums.filter(function (w) { return w > lastFilled; })[0];
    if (!firstWeek) { return { ok: false, error: 'Alle Week-kolommen zijn al gevuld' }; }
    var first = entries.map(function (e) { return e.date; }).sort()[0];
    anchor = { monday: monday_(first).toISOString().slice(0, 10), week: firstWeek };
  }
  var anchorMs = monday_(anchor.monday).getTime();

  // Latest session per exercise per week
  var latest = {};
  entries.forEach(function (e) {
    var w = anchor.week + Math.round((monday_(e.date).getTime() - anchorMs) / (7 * 864e5));
    var key = e.id + '|' + w;
    if (!latest[key] || latest[key].date < e.date) { latest[key] = { id: e.id, week: w, date: e.date, sets: e.sets }; }
  });

  var changes = [];
  var skipped = [];
  Object.keys(latest).forEach(function (key) {
    var s = latest[key];
    var cols = lay.weeks[s.week];
    if (!cols) { skipped.push(s.id + ' (' + s.date + ', week ' + s.week + ')'); return; }
    var row = lay.rows[s.id];
    var d = describe_(s.sets);
    [[cols.kg, d.weight], [cols.reps, d.reps]].forEach(function (cell) {
      if (values[row - 1][cell[0] - 1] !== cell[1]) {
        changes.push({ row: row, col: cell[0], value: cell[1], week: s.week, id: s.id });
      }
    });
  });

  if (!dryRun) {
    changes.forEach(function (c) {
      sheet.getRange(c.row, c.col).setNumberFormat('@').setValue(c.value);
    });
    props.setProperty('ANCHOR', JSON.stringify(anchor));
  }
  return {
    ok: true,
    changed: changes.length,
    weeks: changes.map(function (c) { return c.week; }).filter(function (w, i, a) { return a.indexOf(w) === i; }),
    skipped: skipped,
    anchor: anchor
  };
}
