/**
 * PAM Core — Pure JavaScript implementation of the Portable Agent Memory format.
 * Browser-compatible: uses SHA-256 via Web Crypto API (BLAKE3 not available in browsers).
 */

class PamArtifact {
  constructor() {
    this.version = "1.0";
    this.source_agent = {
      name: "browser-extension",
      model_family: "user",
      runtime: "chrome",
      version: "0.1.0"
    };
    this.created_at = new Date().toISOString();
    this.updated_at = new Date().toISOString();
    this.episodic = [];
    this.semantic = [];
    this.procedural = [];
    this.working = [];
    this.identity = [];
    this.root_hash = "";
    this.signature = "";
  }

  async addEpisodic(content, eventType = "observation") {
    const entry = {
      content,
      event_type: eventType,
      timestamp: new Date().toISOString(),
      importance: 0.5
    };
    entry.id = await this.computeId(entry);
    this.episodic.push(entry);
    this.updated_at = new Date().toISOString();
    return entry;
  }

  async addSemantic(subject, predicate, object, confidence = 1.0) {
    const entry = {
      subject,
      predicate,
      object,
      confidence,
      timestamp: new Date().toISOString()
    };
    entry.id = await this.computeId(entry);
    this.semantic.push(entry);
    this.updated_at = new Date().toISOString();
    return entry;
  }

  async addProcedural(name, description, steps = [], language = "natural") {
    const entry = {
      name,
      description,
      steps,
      language,
      timestamp: new Date().toISOString()
    };
    entry.id = await this.computeId(entry);
    this.procedural.push(entry);
    this.updated_at = new Date().toISOString();
    return entry;
  }

  async addWorking(content, goals = [], context = {}) {
    const entry = {
      content,
      goals,
      context,
      timestamp: new Date().toISOString()
    };
    entry.id = await this.computeId(entry);
    this.working.push(entry);
    this.updated_at = new Date().toISOString();
    return entry;
  }

  async addIdentity(key, value) {
    const entry = {
      key,
      value,
      timestamp: new Date().toISOString()
    };
    entry.id = await this.computeId(entry);
    this.identity.push(entry);
    this.updated_at = new Date().toISOString();
    return entry;
  }

  async computeId(entry) {
    const keys = Object.keys(entry).filter(k => k !== 'id').sort();
    const data = JSON.stringify(entry, keys);
    const hash = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(data));
    return 'sha256:' + Array.from(new Uint8Array(hash)).map(b => b.toString(16).padStart(2, '0')).join('');
  }

  async computeRootHash() {
    const allEntries = [
      ...this.episodic,
      ...this.semantic,
      ...this.procedural,
      ...this.working,
      ...this.identity
    ];
    const ids = allEntries.map(e => e.id).sort();
    const combined = ids.join('|');
    const hash = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(combined));
    this.root_hash = 'sha256:' + Array.from(new Uint8Array(hash)).map(b => b.toString(16).padStart(2, '0')).join('');
    return this.root_hash;
  }

  async toJSON() {
    await this.computeRootHash();
    return JSON.stringify(this, null, 2);
  }

  toPlainObject() {
    return {
      version: this.version,
      source_agent: this.source_agent,
      created_at: this.created_at,
      updated_at: this.updated_at,
      episodic: this.episodic,
      semantic: this.semantic,
      procedural: this.procedural,
      working: this.working,
      identity: this.identity,
      root_hash: this.root_hash,
      signature: this.signature
    };
  }

  static fromObject(obj) {
    const pam = new PamArtifact();
    pam.version = obj.version || "1.0";
    pam.source_agent = obj.source_agent || pam.source_agent;
    pam.created_at = obj.created_at || pam.created_at;
    pam.updated_at = obj.updated_at || pam.updated_at;
    pam.episodic = obj.episodic || [];
    pam.semantic = obj.semantic || [];
    pam.procedural = obj.procedural || [];
    pam.working = obj.working || [];
    pam.identity = obj.identity || [];
    pam.root_hash = obj.root_hash || "";
    pam.signature = obj.signature || "";
    return pam;
  }

  static fromJSON(json) {
    const obj = typeof json === 'string' ? JSON.parse(json) : json;
    return PamArtifact.fromObject(obj);
  }

  getStats() {
    return {
      episodic: this.episodic.length,
      semantic: this.semantic.length,
      procedural: this.procedural.length,
      working: this.working.length,
      identity: this.identity.length,
      total: this.episodic.length + this.semantic.length + this.procedural.length + this.working.length + this.identity.length
    };
  }

  toPromptContext(task = "") {
    const parts = [];
    parts.push("[Memory Context from Portable Agent Memory]");

    if (this.identity.length) {
      parts.push("\n## Identity");
      this.identity.forEach(e => parts.push(`- ${e.key}: ${e.value}`));
    }

    if (this.episodic.length) {
      parts.push("\n## Recent Events");
      this.episodic.slice(-10).forEach(e => parts.push(`- [${e.event_type}] ${e.content}`));
    }

    if (this.semantic.length) {
      parts.push("\n## Known Facts");
      this.semantic.forEach(e => parts.push(`- ${e.subject} ${e.predicate} ${e.object} (confidence: ${e.confidence})`));
    }

    if (this.procedural.length) {
      parts.push("\n## Skills");
      this.procedural.forEach(e => parts.push(`- ${e.name}: ${e.description}`));
    }

    if (this.working.length) {
      parts.push("\n## Working Memory");
      this.working.forEach(e => parts.push(`- ${e.content}`));
    }

    if (task) {
      parts.push(`\n## Current Task\n${task}`);
    }

    return parts.join("\n");
  }

  removeEntry(id) {
    for (const category of ['episodic', 'semantic', 'procedural', 'working', 'identity']) {
      const idx = this[category].findIndex(e => e.id === id);
      if (idx !== -1) {
        this[category].splice(idx, 1);
        this.updated_at = new Date().toISOString();
        return true;
      }
    }
    return false;
  }

  search(query) {
    const q = query.toLowerCase();
    const results = [];

    this.episodic.forEach(e => {
      if (e.content.toLowerCase().includes(q)) results.push({ ...e, category: 'episodic' });
    });
    this.semantic.forEach(e => {
      const text = `${e.subject} ${e.predicate} ${e.object}`;
      if (text.toLowerCase().includes(q)) results.push({ ...e, category: 'semantic' });
    });
    this.procedural.forEach(e => {
      const text = `${e.name} ${e.description}`;
      if (text.toLowerCase().includes(q)) results.push({ ...e, category: 'procedural' });
    });
    this.working.forEach(e => {
      if (e.content.toLowerCase().includes(q)) results.push({ ...e, category: 'working' });
    });
    this.identity.forEach(e => {
      const text = `${e.key} ${e.value}`;
      if (text.toLowerCase().includes(q)) results.push({ ...e, category: 'identity' });
    });

    return results;
  }
}

// Make available in different contexts
if (typeof globalThis !== 'undefined') {
  globalThis.PamArtifact = PamArtifact;
}
if (typeof window !== 'undefined') {
  window.PamArtifact = PamArtifact;
}
