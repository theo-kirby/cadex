// SPDX-License-Identifier: LGPL-2.1-or-later
export function parseStl(buffer) {
    var bytes = new Uint8Array(buffer);
    var head = '';
    for (var i = 0; i < Math.min(bytes.length, 400); i++) head += String.fromCharCode(bytes[i]);
    var looksAscii = /^\s*solid/.test(head) && head.indexOf('facet') >= 0;
    if (!looksAscii && bytes.length >= 84) {
      var view = new DataView(buffer);
      var count = view.getUint32(80, true);
      if (84 + count * 50 === bytes.length) {
        var out = new Float32Array(count * 9);
        var offset = 84;
        for (var t = 0; t < count; t++) {
          for (var k = 0; k < 9; k++) out[t * 9 + k] = view.getFloat32(offset + 12 + k * 4, true);
          offset += 50;
        }
        return out;
      }
    }
    var text = new TextDecoder().decode(bytes);
    var re = /vertex\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)/g;
    var values = [];
    var m;
    while ((m = re.exec(text)) !== null) values.push(+m[1], +m[2], +m[3]);
    var usable = values.length - (values.length % 9);
    return new Float32Array(values.slice(0, usable));
  }

