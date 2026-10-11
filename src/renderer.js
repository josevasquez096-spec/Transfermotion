import { N } from './skeleton.js';

const VS = `
attribute vec2 a_pos;
attribute vec2 a_uv;
attribute vec4 a_idx;
attribute vec4 a_w;
uniform vec4 u_bones[${N}];
uniform vec2 u_res;
uniform vec2 u_offset;
varying vec2 v_uv;

vec2 xf(float i, vec2 p) {
  vec4 b = u_bones[int(i + 0.5)];
  return vec2(b.x * p.x - b.y * p.y + b.z, b.y * p.x + b.x * p.y + b.w);
}

void main() {
  vec2 p = xf(a_idx.x, a_pos) * a_w.x + xf(a_idx.y, a_pos) * a_w.y
         + xf(a_idx.z, a_pos) * a_w.z + xf(a_idx.w, a_pos) * a_w.w;
  vec2 c = (p + u_offset) / u_res * 2.0 - 1.0;
  gl_Position = vec4(c.x, -c.y, 0.0, 1.0);
  v_uv = a_uv;
}`;

const FS = `
precision mediump float;
uniform sampler2D u_tex;
uniform float u_wire;
varying vec2 v_uv;
void main() {
  vec4 c = texture2D(u_tex, v_uv);
  if (u_wire > 0.5) { gl_FragColor = vec4(0.49, 0.95, 0.78, 1.0) * 0.6; return; }
  if (c.a < 0.01) discard;
  gl_FragColor = c;
}`;

function shader(gl, type, src) {
  const s = gl.createShader(type);
  gl.shaderSource(s, src);
  gl.compileShader(s);
  if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
  return s;
}

// Dibuja la imagen del personaje deformada por los huesos (skinning en GPU).
export class Renderer {
  constructor(canvas) {
    this.canvas = canvas;
    const gl = canvas.getContext('webgl', { premultipliedAlpha: true, preserveDrawingBuffer: true, alpha: true });
    if (!gl) throw new Error('WebGL no está disponible en este navegador.');
    this.gl = gl;
    const prog = gl.createProgram();
    gl.attachShader(prog, shader(gl, gl.VERTEX_SHADER, VS));
    gl.attachShader(prog, shader(gl, gl.FRAGMENT_SHADER, FS));
    gl.linkProgram(prog);
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(prog));
    gl.useProgram(prog);
    this.prog = prog;
    this.loc = {
      pos: gl.getAttribLocation(prog, 'a_pos'),
      uv: gl.getAttribLocation(prog, 'a_uv'),
      idx: gl.getAttribLocation(prog, 'a_idx'),
      w: gl.getAttribLocation(prog, 'a_w'),
      bones: gl.getUniformLocation(prog, 'u_bones'),
      res: gl.getUniformLocation(prog, 'u_res'),
      offset: gl.getUniformLocation(prog, 'u_offset'),
      wire: gl.getUniformLocation(prog, 'u_wire'),
    };
    this.buffers = {
      pos: gl.createBuffer(), uv: gl.createBuffer(), idx: gl.createBuffer(), w: gl.createBuffer(), el: gl.createBuffer(),
    };
    this.wireBuffer = gl.createBuffer();
    this.tex = gl.createTexture();
    this.count = 0;
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
  }

  setTexture(source) {
    const gl = this.gl;
    gl.bindTexture(gl.TEXTURE_2D, this.tex);
    gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, true);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, source);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  }

  setMesh(mesh) {
    const gl = this.gl, b = this.buffers, l = this.loc;
    const attr = (buf, data, loc, size) => {
      gl.bindBuffer(gl.ARRAY_BUFFER, buf);
      gl.bufferData(gl.ARRAY_BUFFER, data, gl.STATIC_DRAW);
      gl.enableVertexAttribArray(loc);
      gl.vertexAttribPointer(loc, size, gl.FLOAT, false, 0, 0);
    };
    attr(b.pos, mesh.pos, l.pos, 2);
    attr(b.uv, mesh.uv, l.uv, 2);
    attr(b.idx, mesh.idx, l.idx, 4);
    attr(b.w, mesh.wts, l.w, 4);
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, b.el);
    gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, mesh.indices, gl.STATIC_DRAW);
    this.count = mesh.indices.length;

    // Índices de líneas para ver la malla (modo depuración).
    const t = mesh.indices, lines = new Uint16Array(t.length * 2);
    for (let i = 0; i < t.length; i += 3) {
      lines.set([t[i], t[i + 1], t[i + 1], t[i + 2], t[i + 2], t[i]], i * 2);
    }
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, this.wireBuffer);
    gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, lines, gl.STATIC_DRAW);
    this.wireCount = lines.length;
  }

  resize(w, h) {
    if (this.canvas.width !== w || this.canvas.height !== h) {
      this.canvas.width = w;
      this.canvas.height = h;
    }
  }

  render(bones, offset, bg, wire = false) {
    const gl = this.gl, l = this.loc;
    gl.viewport(0, 0, this.canvas.width, this.canvas.height);
    if (bg) gl.clearColor(bg[0] * bg[3], bg[1] * bg[3], bg[2] * bg[3], bg[3]);
    else gl.clearColor(0, 0, 0, 0);
    gl.clear(gl.COLOR_BUFFER_BIT);
    if (!this.count) return;
    gl.uniform4fv(l.bones, bones);
    gl.uniform2f(l.res, this.canvas.width, this.canvas.height);
    gl.uniform2f(l.offset, offset[0], offset[1]);
    gl.bindTexture(gl.TEXTURE_2D, this.tex);
    gl.uniform1f(l.wire, 0);
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, this.buffers.el);
    gl.drawElements(gl.TRIANGLES, this.count, gl.UNSIGNED_SHORT, 0);
    if (wire) {
      gl.uniform1f(l.wire, 1);
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, this.wireBuffer);
      gl.drawElements(gl.LINES, this.wireCount, gl.UNSIGNED_SHORT, 0);
    }
  }
}
