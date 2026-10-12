import { N } from './skeleton.js';

// Ubicaciones fijas de los atributos, iguales en ambos programas (WebGL1 no tiene VAOs).
const A_POS = 0, A_UV = 1, A_IDX = 2, A_W = 3;

// Programa con skinning: la imagen del personaje deformada por los huesos.
// Espacio posado → canvas: p * u_scale + u_offset.
const VS = `
attribute vec2 a_pos;
attribute vec2 a_uv;
attribute vec4 a_idx;
attribute vec4 a_w;
uniform vec4 u_bones[${N}];
uniform vec2 u_res;
uniform vec2 u_offset;
uniform float u_scale;
varying vec2 v_uv;

vec2 xf(float i, vec2 p) {
  vec4 b = u_bones[int(i + 0.5)];
  return vec2(b.x * p.x - b.y * p.y + b.z, b.y * p.x + b.x * p.y + b.w);
}

void main() {
  vec2 p = xf(a_idx.x, a_pos) * a_w.x + xf(a_idx.y, a_pos) * a_w.y
         + xf(a_idx.z, a_pos) * a_w.z + xf(a_idx.w, a_pos) * a_w.w;
  vec2 c = (p * u_scale + u_offset) / u_res * 2.0 - 1.0;
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

// Programa "plano": mallas dinámicas cuyas posiciones ya vienen en espacio posado (cara y boca).
const PLAIN_VS = `
attribute vec2 a_pos;
attribute vec2 a_uv;
uniform vec2 u_res;
uniform vec2 u_offset;
uniform float u_scale;
varying vec2 v_uv;
void main() {
  vec2 c = (a_pos * u_scale + u_offset) / u_res * 2.0 - 1.0;
  gl_Position = vec4(c.x, -c.y, 0.0, 1.0);
  v_uv = a_uv;
}`;

// u_mode: 0 = textura normal, 1 = boca sacada del video, 2 = boca procedural, 3 = alambre (depuración).
const PLAIN_FS = `
precision mediump float;
uniform sampler2D u_tex;
uniform float u_mode;
uniform vec3 u_lip;
uniform vec3 u_skin;
varying vec2 v_uv;
void main() {
  if (u_mode < 0.5) {
    vec4 c = texture2D(u_tex, v_uv);
    if (c.a < 0.01) discard;
    gl_FragColor = c;
  } else if (u_mode < 1.5) {
    // Interior de la boca del video recoloreado con el personaje: la cavidad y la lengua toman el color
    // de sus labios y los dientes (claros y poco saturados) un blanco ajustado a su piel.
    vec3 c = texture2D(u_tex, v_uv).rgb;
    float lum = dot(c, vec3(0.299, 0.587, 0.114));
    float sat = max(c.r, max(c.g, c.b)) - min(c.r, min(c.g, c.b));
    float light = clamp(dot(u_skin, vec3(0.299, 0.587, 0.114)) / 0.62, 0.55, 1.1);
    vec3 cavity = u_lip * (0.22 + 1.05 * lum);
    vec3 teeth = mix(vec3(0.96, 0.94, 0.9), u_skin, 0.15) * (0.55 + 0.45 * lum) * light;
    float t = smoothstep(0.36, 0.68, lum) * (1.0 - smoothstep(0.16, 0.42, sat));
    gl_FragColor = vec4(mix(cavity, teeth, t), 1.0);
  } else if (u_mode < 2.5) {
    // Sin video: cavidad roja oscura, lengua abajo y dientes arriba (v_uv = caja de la boca en 0..1).
    vec2 q = (v_uv - 0.5) * 2.0;
    vec3 col = mix(vec3(0.07, 0.01, 0.02), vec3(0.42, 0.1, 0.11), smoothstep(0.15, 1.0, length(q)));
    col = mix(col, vec3(0.55, 0.2, 0.22), smoothstep(0.55, 0.95, v_uv.y) * (1.0 - smoothstep(0.5, 0.9, abs(q.x))));
    float teeth = (1.0 - smoothstep(0.16, 0.26, v_uv.y)) * (1.0 - smoothstep(0.45, 0.75, abs(q.x)));
    gl_FragColor = vec4(mix(col, vec3(0.9, 0.88, 0.83), teeth), 1.0);
  } else {
    gl_FragColor = vec4(0.97, 0.55, 0.85, 1.0) * 0.6;
  }
}`;

function shader(gl, type, src) {
  const s = gl.createShader(type);
  gl.shaderSource(s, src);
  gl.compileShader(s);
  if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
  return s;
}

function program(gl, vs, fs, attribs) {
  const prog = gl.createProgram();
  gl.attachShader(prog, shader(gl, gl.VERTEX_SHADER, vs));
  gl.attachShader(prog, shader(gl, gl.FRAGMENT_SHADER, fs));
  attribs.forEach((name, i) => gl.bindAttribLocation(prog, i, name));
  gl.linkProgram(prog);
  if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(prog));
  return prog;
}

// Sin mipmaps y con bordes fijos: así sirve para cualquier tamaño en WebGL1 (también en iPhone).
function texture(gl, rgba) {
  const t = gl.createTexture();
  gl.bindTexture(gl.TEXTURE_2D, t);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 1, 1, 0, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array(rgba));
  return t;
}

function upload(gl, tex, source, premultiply) {
  gl.bindTexture(gl.TEXTURE_2D, tex);
  gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, premultiply);
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, source);
}

function attrib(gl, loc, buf, size) {
  gl.bindBuffer(gl.ARRAY_BUFFER, buf);
  gl.enableVertexAttribArray(loc);
  gl.vertexAttribPointer(loc, size, gl.FLOAT, false, 0, 0);
}

// Índices de líneas (aristas de cada triángulo) para ver la malla.
function wireIndices(t, count) {
  const lines = new Uint16Array(count * 2);
  for (let i = 0; i < count; i += 3) {
    lines.set([t[i], t[i + 1], t[i + 1], t[i + 2], t[i + 2], t[i]], i * 2);
  }
  return lines;
}

// Dibuja el personaje: capa del cuerpo con skinning, interior de la boca, cara animada
// (malla dinámica) y por delante brazos y piernas.
export class Renderer {
  constructor(canvas) {
    this.canvas = canvas;
    const gl = canvas.getContext('webgl', { premultipliedAlpha: true, preserveDrawingBuffer: true, alpha: true });
    if (!gl) throw new Error('WebGL no está disponible en este navegador.');
    this.gl = gl;
    this.prog = program(gl, VS, FS, ['a_pos', 'a_uv', 'a_idx', 'a_w']);
    this.plain = program(gl, PLAIN_VS, PLAIN_FS, ['a_pos', 'a_uv']);
    const u = (p, name) => gl.getUniformLocation(p, name);
    this.loc = {
      bones: u(this.prog, 'u_bones'), res: u(this.prog, 'u_res'), offset: u(this.prog, 'u_offset'),
      scale: u(this.prog, 'u_scale'), wire: u(this.prog, 'u_wire'),
    };
    this.ploc = {
      res: u(this.plain, 'u_res'), offset: u(this.plain, 'u_offset'), scale: u(this.plain, 'u_scale'),
      mode: u(this.plain, 'u_mode'), lip: u(this.plain, 'u_lip'), skin: u(this.plain, 'u_skin'),
    };
    this.buffers = {
      pos: gl.createBuffer(), uv: gl.createBuffer(), idx: gl.createBuffer(), w: gl.createBuffer(), el: gl.createBuffer(),
    };
    this.wireBuffer = gl.createBuffer();
    this.count = 0;
    this.bodyCount = 0;
    this.wireCount = 0;
    // Cara: UVs e índices fijos, posiciones nuevas en cada fotograma.
    this.face = {
      pos: gl.createBuffer(), uv: gl.createBuffer(), el: gl.createBuffer(), wire: gl.createBuffer(),
      n: 0, count: 0, wireCount: 0,
    };
    // Boca: lista de triángulos que cambia en cada fotograma (capacidad en bytes).
    this.mouth = { pos: gl.createBuffer(), uv: gl.createBuffer(), cap: 0, box: new Float32Array(0) };
    this.tex = texture(gl, [0, 0, 0, 0]);
    this.faceTex = texture(gl, [0, 0, 0, 0]);
    this.videoTex = texture(gl, [18, 4, 6, 255]);
    this.hasFaceTexture = false;
    this.hasVideoTexture = false;
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
  }

  setTexture(source) {
    upload(this.gl, this.tex, source, true);
  }

  // Textura de la cara: la imagen completa del personaje (las UVs de la cara son rest / [imgW, imgH]).
  setFaceTexture(canvas) {
    if (!canvas) {
      this.hasFaceTexture = false;
      return;
    }
    upload(this.gl, this.faceTex, canvas, true);
    this.hasFaceTexture = true;
  }

  // Fotograma actual de la fuente (video o canvas) para el interior de la boca.
  // Devuelve false si aún no hay imagen o el navegador no deja leerla (video de otro dominio).
  updateVideoTexture(video) {
    if (!video || (video.readyState !== undefined && video.readyState < 2)) return false;
    if (!(video.videoWidth ?? video.width) || !(video.videoHeight ?? video.height)) return false;
    try {
      upload(this.gl, this.videoTex, video, false);
      this.hasVideoTexture = true;
    } catch (err) {
      this.hasVideoTexture = false;
    }
    return this.hasVideoTexture;
  }

  // Olvida el último fotograma (p. ej. al cambiar de fuente): la boca pasa a ser procedural.
  clearVideoTexture() {
    this.hasVideoTexture = false;
  }

  // mesh.bodyCount = cuántos índices (al principio) son de la capa del cuerpo; el resto son extremidades.
  setMesh(mesh) {
    const gl = this.gl, b = this.buffers;
    const data = (buf, arr) => {
      gl.bindBuffer(gl.ARRAY_BUFFER, buf);
      gl.bufferData(gl.ARRAY_BUFFER, arr, gl.STATIC_DRAW);
    };
    data(b.pos, mesh.pos);
    data(b.uv, mesh.uv);
    data(b.idx, mesh.idx);
    data(b.w, mesh.wts);
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, b.el);
    gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, mesh.indices, gl.STATIC_DRAW);
    this.count = mesh.indices.length - (mesh.indices.length % 3);
    const body = Math.max(0, Math.min(this.count, mesh.bodyCount ?? this.count));
    this.bodyCount = body - (body % 3);

    const lines = wireIndices(mesh.indices, this.count);
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, this.wireBuffer);
    gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, lines, gl.STATIC_DRAW);
    this.wireCount = lines.length;
  }

  // Malla de la cara: {uv: Float32Array(n*2), indices: Uint16Array}. null la quita.
  setFaceMesh(mesh) {
    const gl = this.gl, f = this.face;
    f.n = f.count = f.wireCount = 0;
    if (!mesh) return;
    const n = mesh.uv.length >> 1;
    let max = -1;
    for (let i = 0; i < mesh.indices.length; i++) if (mesh.indices[i] > max) max = mesh.indices[i];
    if (!n || n > 65535 || max >= n) {
      console.warn('Malla de la cara no válida: no se dibujará.');
      return;
    }
    const indices = mesh.indices instanceof Uint16Array ? mesh.indices : Uint16Array.from(mesh.indices);
    const count = indices.length - (indices.length % 3);
    gl.bindBuffer(gl.ARRAY_BUFFER, f.pos);
    gl.bufferData(gl.ARRAY_BUFFER, n * 8, gl.DYNAMIC_DRAW);
    gl.bindBuffer(gl.ARRAY_BUFFER, f.uv);
    gl.bufferData(gl.ARRAY_BUFFER, mesh.uv instanceof Float32Array ? mesh.uv : new Float32Array(mesh.uv), gl.STATIC_DRAW);
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, f.el);
    gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, indices, gl.STATIC_DRAW);
    const lines = wireIndices(indices, count);
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, f.wire);
    gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, lines, gl.STATIC_DRAW);
    f.n = n;
    f.count = count;
    f.wireCount = lines.length;
  }

  resize(w, h) {
    if (this.canvas.width !== w || this.canvas.height !== h) {
      this.canvas.width = w;
      this.canvas.height = h;
    }
  }

  useSkinned() {
    const gl = this.gl, b = this.buffers;
    gl.useProgram(this.prog);
    attrib(gl, A_POS, b.pos, 2);
    attrib(gl, A_UV, b.uv, 2);
    attrib(gl, A_IDX, b.idx, 4);
    attrib(gl, A_W, b.w, 4);
    gl.bindTexture(gl.TEXTURE_2D, this.tex);
  }

  usePlain(pos, uv, tex, mode) {
    const gl = this.gl;
    gl.useProgram(this.plain);
    gl.disableVertexAttribArray(A_IDX);
    gl.disableVertexAttribArray(A_W);
    attrib(gl, A_POS, pos, 2);
    attrib(gl, A_UV, uv, 2);
    gl.bindTexture(gl.TEXTURE_2D, tex);
    gl.uniform1f(this.ploc.mode, mode);
  }

  // Interior de la boca (lista de triángulos). Sin fotograma de video se usa la boca procedural.
  drawMouth(m) {
    const gl = this.gl, M = this.mouth;
    const verts = Math.floor(m.positions.length / 6) * 3;
    if (!verts) return;
    const fromVideo = m.mode === 1 && this.hasVideoTexture && m.uvs && m.uvs.length >= verts * 2;
    const bytes = verts * 8;
    if (bytes > M.cap) {
      M.cap = Math.max(bytes, M.cap * 2, 1024);
      for (const buf of [M.pos, M.uv]) {
        gl.bindBuffer(gl.ARRAY_BUFFER, buf);
        gl.bufferData(gl.ARRAY_BUFFER, M.cap, gl.DYNAMIC_DRAW);
      }
    }
    const P = m.positions;
    gl.bindBuffer(gl.ARRAY_BUFFER, M.pos);
    gl.bufferSubData(gl.ARRAY_BUFFER, 0, P.length === verts * 2 ? P : P.subarray(0, verts * 2));
    gl.bindBuffer(gl.ARRAY_BUFFER, M.uv);
    if (fromVideo) {
      gl.bufferSubData(gl.ARRAY_BUFFER, 0, m.uvs.length === verts * 2 ? m.uvs : m.uvs.subarray(0, verts * 2));
    } else {
      // Coordenadas del degradado: la caja que envuelve la boca, normalizada a 0..1.
      if (M.box.length < verts * 2) M.box = new Float32Array(verts * 2);
      let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
      for (let i = 0; i < verts * 2; i += 2) {
        x0 = Math.min(x0, P[i]); x1 = Math.max(x1, P[i]);
        y0 = Math.min(y0, P[i + 1]); y1 = Math.max(y1, P[i + 1]);
      }
      const sx = 1 / Math.max(x1 - x0, 1e-6), sy = 1 / Math.max(y1 - y0, 1e-6);
      for (let i = 0; i < verts * 2; i += 2) {
        M.box[i] = (P[i] - x0) * sx;
        M.box[i + 1] = (P[i + 1] - y0) * sy;
      }
      gl.bufferSubData(gl.ARRAY_BUFFER, 0, M.box.subarray(0, verts * 2));
    }
    this.usePlain(M.pos, M.uv, this.videoTex, fromVideo ? 1 : 2);
    const lip = m.lip ?? [0.55, 0.22, 0.24], skin = m.skin ?? [0.85, 0.68, 0.58];
    gl.uniform3f(this.ploc.lip, lip[0], lip[1], lip[2]);
    gl.uniform3f(this.ploc.skin, skin[0], skin[1], skin[2]);
    gl.drawArrays(gl.TRIANGLES, 0, verts);
  }

  // Dibuja la cara con sus posiciones del fotograma (espacio posado, n*2 valores). Devuelve si se dibujó.
  drawFace(positions) {
    const gl = this.gl, f = this.face;
    if (!f.count || !this.hasFaceTexture || !positions || positions.length < f.n * 2) return false;
    gl.bindBuffer(gl.ARRAY_BUFFER, f.pos);
    gl.bufferSubData(gl.ARRAY_BUFFER, 0, positions.length === f.n * 2 ? positions : positions.subarray(0, f.n * 2));
    this.usePlain(f.pos, f.uv, this.faceTex, 0);
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, f.el);
    gl.drawElements(gl.TRIANGLES, f.count, gl.UNSIGNED_SHORT, 0);
    return true;
  }

  // render({ bones, view: {scale, ox, oy}, bg, wire, face: {positions} | null,
  //          mouth: {positions, uvs, mode, lip?: [r,g,b], skin?: [r,g,b]} | null })
  // canvas = posado * view.scale + [view.ox, view.oy]. Orden: cuerpo, boca, cara, extremidades, alambre.
  // También acepta la forma anterior render(bones, offset, bg, wire), equivalente a view = {scale: 1, ox, oy}.
  render(opts, ...legacy) {
    if (ArrayBuffer.isView(opts) || Array.isArray(opts)) {
      const [offset = [0, 0], bg, wire] = legacy;
      opts = { bones: opts, view: { scale: 1, ox: offset[0], oy: offset[1] }, bg, wire };
    }
    const { bones, view, bg = null, wire = false, face = null, mouth = null } = opts;
    const gl = this.gl, l = this.loc, p = this.ploc;
    if (gl.isContextLost()) return;
    const W = this.canvas.width, H = this.canvas.height;
    gl.viewport(0, 0, W, H);
    if (bg) gl.clearColor(bg[0] * bg[3], bg[1] * bg[3], bg[2] * bg[3], bg[3]);
    else gl.clearColor(0, 0, 0, 0);
    gl.clear(gl.COLOR_BUFFER_BIT);
    const s = view?.scale ?? 1, ox = view?.ox ?? 0, oy = view?.oy ?? 0;
    const skinned = this.count > 0 && !!bones;

    gl.activeTexture(gl.TEXTURE0);
    gl.useProgram(this.plain);
    gl.uniform2f(p.res, W, H);
    gl.uniform2f(p.offset, ox, oy);
    gl.uniform1f(p.scale, s);
    if (skinned) {
      gl.useProgram(this.prog);
      gl.uniform4fv(l.bones, bones);
      gl.uniform2f(l.res, W, H);
      gl.uniform2f(l.offset, ox, oy);
      gl.uniform1f(l.scale, s);
      gl.uniform1f(l.wire, 0);
      if (this.bodyCount) {
        this.useSkinned();
        gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, this.buffers.el);
        gl.drawElements(gl.TRIANGLES, this.bodyCount, gl.UNSIGNED_SHORT, 0);
      }
    }
    if (mouth?.positions) this.drawMouth(mouth);
    const faceDrawn = face ? this.drawFace(face.positions) : false;
    if (skinned && this.count > this.bodyCount) {
      this.useSkinned();
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, this.buffers.el);
      gl.drawElements(gl.TRIANGLES, this.count - this.bodyCount, gl.UNSIGNED_SHORT, this.bodyCount * 2);
    }
    if (wire) {
      if (skinned) {
        this.useSkinned();
        gl.uniform1f(l.wire, 1);
        gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, this.wireBuffer);
        gl.drawElements(gl.LINES, this.wireCount, gl.UNSIGNED_SHORT, 0);
        gl.uniform1f(l.wire, 0);
      }
      if (faceDrawn) {
        const f = this.face;
        this.usePlain(f.pos, f.uv, this.faceTex, 3);
        gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, f.wire);
        gl.drawElements(gl.LINES, f.wireCount, gl.UNSIGNED_SHORT, 0);
      }
    }
  }
}
