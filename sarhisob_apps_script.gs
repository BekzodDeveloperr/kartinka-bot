/**
 * Sarhisob → Extensions (Kengaytmalar) → Apps Script ga shu kodni qo'ying.
 * Deploy → New deployment → Web app → Execute as: Me, Who has access: Anyone → Deploy.
 * Chiqqan havolani (…/exec) Railway'da SHEET_WEBHOOK_URL ga qo'ying.
 */
function doPost(e) {
  var d = JSON.parse(e.postData.contents);
  var sh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('Sheet1');
  var lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try {
    // B ustunidagi birinchi bo'sh qatorni topamiz (3-qatordan boshlab)
    var names = sh.getRange('B3:B1000').getValues();
    var row = 3;
    for (var i = 0; i < names.length; i++) {
      if (String(names[i][0]).trim() === '') { row = 3 + i; break; }
    }
    var no = row - 2;
    // A..K: No, Ism, Telefon, Sana, Manager, Fon, Razmer, Jami, To'langan, Qoldiq, Manzil
    sh.getRange(row, 1, 1, 11).setValues([[
      no, d.ism, d.telefon, new Date(d.sana), d.manager, d.fon, d.razmer,
      d.jami, d.tolangan, d.qoldiq, d.manzil
    ]]);
    sh.getRange(row, 15).setValue(d.izoh); // O: Izoh
    return ContentService.createTextOutput('ok');
  } finally {
    lock.releaseLock();
  }
}
