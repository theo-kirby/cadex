// SPDX-FileCopyrightText: 2026 Cadex Authors
// SPDX-License-Identifier: LGPL-2.1-or-later
//
// A small markdown subset drawn as DOM (ADR-515), for a run's probe README:
// headings, paragraphs, lists, tables, code fences, block quotes and rules;
// inline code, bold, italics, links and images. Every string lands through
// textContent, so the markdown can carry no markup of its own; an HTML
// comment is dropped. A relative link or image resolves against `base`;
// only http(s) links leave the page, and only relative images load.
(function () {
  'use strict';

  function el(tag, className) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    return node;
  }

  function relative(target) {
    return !/^[a-z][a-z0-9+.-]*:/i.test(target) && target.charAt(0) !== '/' && target.slice(0, 2) !== '//';
  }

  function resolve(target, base) {
    if (target.charAt(0) === '#') return null;
    if (relative(target)) return base + target.replace(/^\.\//, '');
    return /^https?:\/\//i.test(target) ? target : null;
  }

  var INLINE = /(`+)([\s\S]*?)\1|!\[([^\]]*)\]\(([^)\s]+)\)|\[([^\]]+)\]\(([^)\s]+)\)|\*\*([\s\S]+?)\*\*|(^|[^\w*])\*(?![\s*])([\s\S]+?)\*(?!\w)/;

  function inline(parent, text, base) {
    while (text) {
      var match = INLINE.exec(text);
      if (!match) { parent.appendChild(document.createTextNode(text)); return; }
      var at = match.index + (match[8] ? match[8].length : 0);
      if (at) parent.appendChild(document.createTextNode(text.slice(0, at)));
      if (match[1]) {
        var code = el('code');
        code.textContent = match[2];
        parent.appendChild(code);
      } else if (match[4] !== undefined) {
        var src = relative(match[4]) ? resolve(match[4], base) : null;
        if (src) {
          var img = el('img', 'md-image');
          img.src = src;
          img.alt = match[3];
          img.loading = 'lazy';
          parent.appendChild(img);
        } else {
          parent.appendChild(document.createTextNode(match[3]));
        }
      } else if (match[5] !== undefined) {
        var href = resolve(match[6], base);
        var link = href ? el('a') : el('span');
        if (href) link.href = href;
        inline(link, match[5], base);
        parent.appendChild(link);
      } else if (match[7] !== undefined) {
        var strong = el('strong');
        inline(strong, match[7], base);
        parent.appendChild(strong);
      } else {
        var em = el('em');
        inline(em, match[9], base);
        parent.appendChild(em);
      }
      text = text.slice(match.index + match[0].length);
    }
  }

  function cells(line) {
    return line.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map(function (c) { return c.trim(); });
  }

  // Draw `text` into `root`, replacing what it held.
  function render(root, text, base) {
    root.textContent = '';
    var lines = text.replace(/<!--[\s\S]*?-->/g, '').split(/\r?\n/);
    var i = 0;
    var para = [];
    function flush() {
      if (!para.length) return;
      var p = el('p');
      inline(p, para.join(' '), base);
      root.appendChild(p);
      para = [];
    }
    while (i < lines.length) {
      var line = lines[i];
      var heading = /^(#{1,6})\s+(.*)$/.exec(line);
      var item = /^(\s*)([-*]|\d+\.)\s+(.*)$/.exec(line);
      if (!line.trim()) { flush(); i++; continue; }
      if (/^```/.test(line)) {
        flush();
        var pre = el('pre');
        var code = el('code');
        var body = [];
        for (i++; i < lines.length && !/^```/.test(lines[i]); i++) body.push(lines[i]);
        code.textContent = body.join('\n');
        pre.appendChild(code);
        root.appendChild(pre);
        i++;
      } else if (heading) {
        flush();
        var h = el('h' + Math.min(6, heading[1].length + 1));
        inline(h, heading[2], base);
        root.appendChild(h);
        i++;
      } else if (/^(\*\s*){3,}$|^(-\s*){3,}$/.test(line.trim())) {
        flush();
        root.appendChild(el('hr'));
        i++;
      } else if (/^\s*\|/.test(line) && i + 1 < lines.length && /^\s*\|?[\s:|-]+\|[\s:|-]*$/.test(lines[i + 1])) {
        flush();
        var table = el('table', 'grid md-table');
        var head = el('thead');
        var row = el('tr');
        cells(line).forEach(function (c) { var th = el('th'); inline(th, c, base); row.appendChild(th); });
        head.appendChild(row);
        table.appendChild(head);
        var tbody = el('tbody');
        for (i += 2; i < lines.length && /^\s*\|/.test(lines[i]); i++) {
          var tr = el('tr');
          cells(lines[i]).forEach(function (c) { var td = el('td'); inline(td, c, base); tr.appendChild(td); });
          tbody.appendChild(tr);
        }
        table.appendChild(tbody);
        var wrap = el('div', 'md-table-wrap');
        wrap.appendChild(table);
        root.appendChild(wrap);
      } else if (/^>\s?/.test(line)) {
        flush();
        var quote = [];
        for (; i < lines.length && /^>\s?/.test(lines[i]); i++) quote.push(lines[i].replace(/^>\s?/, ''));
        var block = el('blockquote');
        render(block, quote.join('\n'), base);
        root.appendChild(block);
      } else if (item && !para.length) {
        var ordered = /\d/.test(item[2]);
        var list = el(ordered ? 'ol' : 'ul');
        var li = null;
        for (; i < lines.length; i++) {
          var next = /^(\s*)([-*]|\d+\.)\s+(.*)$/.exec(lines[i]);
          if (next) {
            li = el('li');
            li.dataset.text = next[3];
            li.dataset.depth = String(next[1].length >= 2 ? 1 : 0);
            list.appendChild(li);
          } else if (lines[i].trim() && /^\s/.test(lines[i]) && li) {
            li.dataset.text += ' ' + lines[i].trim();
          } else {
            break;
          }
        }
        Array.prototype.forEach.call(list.children, function (node) {
          inline(node, node.dataset.text, base);
          delete node.dataset.text;
        });
        root.appendChild(list);
      } else {
        para.push(line.trim());
        i++;
      }
    }
    flush();
  }

  window.CadexMarkdown = { render: render };
}());
