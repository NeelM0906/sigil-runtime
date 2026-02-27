// Sigil Dashboard — State Management

export class DashboardState {
  constructor() {
    this.current = null;
    this.previous = null;
    this._hashes = {};
    this._prevHashes = {};
  }

  update(data) {
    this.previous = this.current;
    this.current = data;
    this._prevHashes = { ...this._hashes };
    this._hashes = {};
    if (data && typeof data === 'object') {
      for (const key of Object.keys(data)) {
        this._hashes[key] = this._hash(data[key]);
      }
    }
  }

  isDirty(key) {
    if (!this.previous) return true;
    return this._hashes[key] !== this._prevHashes[key];
  }

  get(key) {
    return this.current ? this.current[key] : null;
  }

  getPrev(key) {
    return this.previous ? this.previous[key] : null;
  }

  _hash(val) {
    try {
      return JSON.stringify(val);
    } catch {
      return String(val);
    }
  }
}
