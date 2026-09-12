// SPDX-FileCopyrightText: 2026 Cadex Authors
// SPDX-License-Identifier: LGPL-2.1-or-later
//
// The review viewer: STL meshes in WebGL with orbit and zoom, no library.
// Each component is one buffer of world-space triangles (placement applied
// on load) with flat normals; the camera orbits the bounds' centre.
(function () {
  'use strict';

  var PALETTE = [[91, 157, 205], [222, 143, 71], [106, 178, 112], [196, 104, 180],
                 [220, 200, 90], [120, 120, 200], [200, 110, 110], [110, 190, 190]];
  var BACKGROUND = [0.11, 0.12, 0.14];

  function parseStl(buffer) {
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

  function rotate(q, v) {
    var x = q[0], y = q[1], z = q[2], w = q[3];
    var ix = w * v[0] + y * v[2] - z * v[1];
    var iy = w * v[1] + z * v[0] - x * v[2];
    var iz = w * v[2] + x * v[1] - y * v[0];
    var iw = -x * v[0] - y * v[1] - z * v[2];
    return [ix * w + iw * -x + iy * -z - iz * -y,
            iy * w + iw * -y + iz * -x - ix * -z,
            iz * w + iw * -z + ix * -y - iy * -x];
  }

  function place(positions, placement) {
    if (!placement) return positions;
    var q = placement.rotation_xyzw, p = placement.position_mm;
    var out = new Float32Array(positions.length);
    for (var i = 0; i < positions.length; i += 3) {
      var r = rotate(q, [positions[i], positions[i + 1], positions[i + 2]]);
      out[i] = r[0] + p[0]; out[i + 1] = r[1] + p[1]; out[i + 2] = r[2] + p[2];
    }
    return out;
  }

  function flatNormals(positions) {
    var normals = new Float32Array(positions.length);
    for (var i = 0; i < positions.length; i += 9) {
      var ux = positions[i + 3] - positions[i], uy = positions[i + 4] - positions[i + 1], uz = positions[i + 5] - positions[i + 2];
      var vx = positions[i + 6] - positions[i], vy = positions[i + 7] - positions[i + 1], vz = positions[i + 8] - positions[i + 2];
      var nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx;
      var len = Math.sqrt(nx * nx + ny * ny + nz * nz) || 1;
      nx /= len; ny /= len; nz /= len;
      for (var k = 0; k < 3; k++) { normals[i + k * 3] = nx; normals[i + k * 3 + 1] = ny; normals[i + k * 3 + 2] = nz; }
    }
    return normals;
  }

  function perspective(fovy, aspect, near, far) {
    var f = 1 / Math.tan(fovy / 2), nf = 1 / (near - far);
    return [f / aspect, 0, 0, 0, 0, f, 0, 0, 0, 0, (far + near) * nf, -1, 0, 0, 2 * far * near * nf, 0];
  }

  function normalize(v) { var l = Math.hypot(v[0], v[1], v[2]) || 1; return [v[0] / l, v[1] / l, v[2] / l]; }
  function cross(a, b) { return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]; }
  function dot(a, b) { return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]; }

  function lookAt(eye, target, up) {
    var z = normalize([eye[0] - target[0], eye[1] - target[1], eye[2] - target[2]]);
    var x = normalize(cross(up, z));
    var y = cross(z, x);
    return [x[0], y[0], z[0], 0, x[1], y[1], z[1], 0, x[2], y[2], z[2], 0,
            -dot(x, eye), -dot(y, eye), -dot(z, eye), 1];
  }

  var VERTEX = 'attribute vec3 a_position; attribute vec3 a_normal; uniform mat4 u_view; uniform mat4 u_proj;' +
               'varying vec3 v_normal; void main() { gl_Position = u_proj * u_view * vec4(a_position, 1.0); v_normal = a_normal; }';
  var FRAGMENT = 'precision mediump float; uniform vec3 u_color; uniform vec3 u_light; varying vec3 v_normal;' +
                 'void main() { float d = abs(dot(normalize(v_normal), u_light)); gl_FragColor = vec4(u_color * (0.3 + 0.7 * d), 1.0); }';

  function compile(gl, type, source) {
    var shader = gl.createShader(type);
    gl.shaderSource(shader, source);
    gl.compileShader(shader);
    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(shader));
    return shader;
  }

  function create(canvas) {
    var gl = canvas.getContext('webgl', { preserveDrawingBuffer: true, antialias: true });
    var state = {
      available: !!gl, meshes: [], bounds: null, triangles: 0,
      camera: { yaw: 0.8, pitch: 0.5, distance: 100, target: [0, 0, 0] },
      dragging: false, last: null, pending: false
    };
    if (!gl) {
      return { available: false, load: function () { return Promise.reject(new Error('WebGL unavailable')); },
               clear: function () {}, fit: function () {}, camera: function () { return null; },
               stats: function () { return { components: 0, triangles: 0, available: false }; },
               nonBackgroundPixels: function () { return 0; } };
    }
    var program = gl.createProgram();
    gl.attachShader(program, compile(gl, gl.VERTEX_SHADER, VERTEX));
    gl.attachShader(program, compile(gl, gl.FRAGMENT_SHADER, FRAGMENT));
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(program));
    var loc = {
      position: gl.getAttribLocation(program, 'a_position'), normal: gl.getAttribLocation(program, 'a_normal'),
      view: gl.getUniformLocation(program, 'u_view'), proj: gl.getUniformLocation(program, 'u_proj'),
      color: gl.getUniformLocation(program, 'u_color'), light: gl.getUniformLocation(program, 'u_light')
    };
    gl.enable(gl.DEPTH_TEST);
    gl.clearColor(BACKGROUND[0], BACKGROUND[1], BACKGROUND[2], 1);

    function eye() {
      var c = state.camera, cp = Math.cos(c.pitch);
      return [c.target[0] + c.distance * cp * Math.cos(c.yaw),
              c.target[1] + c.distance * cp * Math.sin(c.yaw),
              c.target[2] + c.distance * Math.sin(c.pitch)];
    }

    function draw() {
      state.pending = false;
      var width = canvas.clientWidth || canvas.width, height = canvas.clientHeight || canvas.height;
      var scale = window.devicePixelRatio || 1;
      if (canvas.width !== Math.floor(width * scale) || canvas.height !== Math.floor(height * scale)) {
        canvas.width = Math.floor(width * scale); canvas.height = Math.floor(height * scale);
      }
      gl.viewport(0, 0, canvas.width, canvas.height);
      gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
      if (!state.meshes.length) return;
      gl.useProgram(program);
      var e = eye(), c = state.camera;
      var radius = state.bounds ? state.bounds.radius : 1;
      var near = Math.max(c.distance - radius * 2, radius * 0.01), far = c.distance + radius * 2;
      gl.uniformMatrix4fv(loc.proj, false, perspective(0.7, canvas.width / canvas.height, near, far));
      gl.uniformMatrix4fv(loc.view, false, lookAt(e, c.target, [0, 0, 1]));
      var light = normalize([e[0] - c.target[0], e[1] - c.target[1], e[2] - c.target[2]]);
      gl.uniform3fv(loc.light, light);
      state.meshes.forEach(function (mesh) {
        gl.bindBuffer(gl.ARRAY_BUFFER, mesh.positions);
        gl.enableVertexAttribArray(loc.position);
        gl.vertexAttribPointer(loc.position, 3, gl.FLOAT, false, 0, 0);
        gl.bindBuffer(gl.ARRAY_BUFFER, mesh.normals);
        gl.enableVertexAttribArray(loc.normal);
        gl.vertexAttribPointer(loc.normal, 3, gl.FLOAT, false, 0, 0);
        gl.uniform3fv(loc.color, mesh.color);
        gl.drawArrays(gl.TRIANGLES, 0, mesh.count);
      });
    }

    function request() {
      if (state.pending) return;
      state.pending = true;
      window.requestAnimationFrame(draw);
    }

    function clear() {
      state.meshes.forEach(function (mesh) { gl.deleteBuffer(mesh.positions); gl.deleteBuffer(mesh.normals); });
      state.meshes = []; state.bounds = null; state.triangles = 0;
      request();
    }

    function fit() {
      if (!state.bounds) return;
      state.camera.target = state.bounds.center.slice();
      state.camera.distance = state.bounds.radius * 2.6 || 100;
      state.camera.yaw = 0.8; state.camera.pitch = 0.5;
      request();
    }

    function upload(name, positions, colorIndex) {
      var normals = flatNormals(positions);
      var pb = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, pb); gl.bufferData(gl.ARRAY_BUFFER, positions, gl.STATIC_DRAW);
      var nb = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, nb); gl.bufferData(gl.ARRAY_BUFFER, normals, gl.STATIC_DRAW);
      var rgb = PALETTE[colorIndex % PALETTE.length];
      state.meshes.push({ name: name, positions: pb, normals: nb, count: positions.length / 3,
                          color: [rgb[0] / 255, rgb[1] / 255, rgb[2] / 255] });
      state.triangles += positions.length / 9;
      var min = state.bounds ? state.bounds.min : [Infinity, Infinity, Infinity];
      var max = state.bounds ? state.bounds.max : [-Infinity, -Infinity, -Infinity];
      for (var i = 0; i < positions.length; i += 3) {
        for (var k = 0; k < 3; k++) { if (positions[i + k] < min[k]) min[k] = positions[i + k]; if (positions[i + k] > max[k]) max[k] = positions[i + k]; }
      }
      var center = [(min[0] + max[0]) / 2, (min[1] + max[1]) / 2, (min[2] + max[2]) / 2];
      var radius = Math.hypot(max[0] - min[0], max[1] - min[1], max[2] - min[2]) / 2 || 1;
      state.bounds = { min: min, max: max, center: center, radius: radius };
    }

    // Load a review model manifest: each component with a mesh URL is fetched,
    // parsed, placed and uploaded; the camera is fitted once everything is in.
    function load(manifest, fetchImpl) {
      clear();
      var fetcher = fetchImpl || window.fetch.bind(window);
      var components = (manifest && manifest.components) || [];
      var loaded = [];
      var jobs = components.map(function (component, index) {
        if (!component.mesh) return Promise.resolve(null);
        return fetcher(component.mesh).then(function (response) {
          if (!response.ok) throw new Error('mesh ' + component.mesh + ': HTTP ' + response.status);
          return response.arrayBuffer();
        }).then(function (buffer) {
          var positions = place(parseStl(buffer), component.placement);
          upload(component.name, positions, index);
          loaded.push({ name: component.name, triangles: positions.length / 9, color: PALETTE[index % PALETTE.length] });
          return loaded[loaded.length - 1];
        });
      });
      return Promise.all(jobs).then(function () { fit(); draw(); return loaded; });
    }

    canvas.addEventListener('mousedown', function (event) {
      state.dragging = true; state.last = [event.clientX, event.clientY]; event.preventDefault();
    });
    window.addEventListener('mousemove', function (event) {
      if (!state.dragging) return;
      var dx = event.clientX - state.last[0], dy = event.clientY - state.last[1];
      state.last = [event.clientX, event.clientY];
      state.camera.yaw -= dx * 0.01;
      state.camera.pitch = Math.max(-1.5, Math.min(1.5, state.camera.pitch + dy * 0.01));
      request();
    });
    window.addEventListener('mouseup', function () { state.dragging = false; });
    canvas.addEventListener('wheel', function (event) {
      event.preventDefault();
      state.camera.distance = Math.max(state.bounds ? state.bounds.radius * 0.2 : 1,
                                       state.camera.distance * Math.exp(event.deltaY * 0.0015));
      request();
    }, { passive: false });
    window.addEventListener('resize', request);

    function nonBackgroundPixels() {
      draw();
      var pixels = new Uint8Array(canvas.width * canvas.height * 4);
      gl.readPixels(0, 0, canvas.width, canvas.height, gl.RGBA, gl.UNSIGNED_BYTE, pixels);
      var bg = [Math.round(BACKGROUND[0] * 255), Math.round(BACKGROUND[1] * 255), Math.round(BACKGROUND[2] * 255)];
      var count = 0;
      for (var i = 0; i < pixels.length; i += 4) {
        if (Math.abs(pixels[i] - bg[0]) + Math.abs(pixels[i + 1] - bg[1]) + Math.abs(pixels[i + 2] - bg[2]) > 12) count++;
      }
      return count;
    }

    return {
      available: true,
      load: load, clear: clear, fit: fit,
      camera: function () { var c = state.camera; return { yaw: c.yaw, pitch: c.pitch, distance: c.distance, target: c.target.slice() }; },
      stats: function () { return { available: true, components: state.meshes.length, triangles: state.triangles,
                                    bounds: state.bounds }; },
      nonBackgroundPixels: nonBackgroundPixels
    };
  }

  window.CadexViewer = { create: create, parseStl: parseStl };
})();
