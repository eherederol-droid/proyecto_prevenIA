/**
 * PrevenIA API Client
 * Handles all communication with the Django REST Framework backend.
 * Automatically attaches JWT token and handles 401 refresh.
 */

const isLocalFrontend = ['localhost', '127.0.0.1'].includes(window.location.hostname)
  && window.location.port === '3000';
const API_BASE = isLocalFrontend
  ? `${window.location.protocol}//${window.location.hostname}:8000/api/v1`
  : '/api/v1';

class PrevenIAClient {
  constructor() {
    this._token = localStorage.getItem('prevenia_token');
    this._refreshToken = localStorage.getItem('prevenia_refresh');
  }

  // =============================================
  // CORE HTTP
  // =============================================

  async _request(method, path, body = null, isFormData = false, responseType = 'json') {
    const headers = {};
    if (this._token) headers['Authorization'] = `Bearer ${this._token}`;
    if (!isFormData) headers['Content-Type'] = 'application/json';

    const opts = {
      method,
      headers,
      body: body ? (isFormData ? body : JSON.stringify(body)) : undefined,
    };

    let res = await fetch(`${API_BASE}${path}`, opts);

    // Auto-refresh token on 401
    if (res.status === 401 && this._refreshToken) {
      const refreshed = await this._refreshAccessToken();
      if (refreshed) {
        headers['Authorization'] = `Bearer ${this._token}`;
        opts.headers = headers;
        res = await fetch(`${API_BASE}${path}`, opts);
      } else {
        this._logout();
        return null;
      }
    }

    if (!res.ok) {
      const responseText = await res.text();
      let error;
      try {
        error = JSON.parse(responseText);
      } catch {
        error = { detail: `El servidor respondió ${res.status} ${res.statusText}`.trim() };
      }
      throw new Error(JSON.stringify(error));
    }

    if (res.status === 204) return null;
    return responseType === 'blob' ? res.blob() : res.json();
  }

  async _refreshAccessToken() {
    try {
      const res = await fetch(`${API_BASE}/auth/refresh/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh: this._refreshToken }),
      });
      if (res.ok) {
        const data = await res.json();
        this._token = data.access;
        localStorage.setItem('prevenia_token', data.access);
        return true;
      }
      return false;
    } catch {
      return false;
    }
  }

  _logout() {
    localStorage.removeItem('prevenia_token');
    localStorage.removeItem('prevenia_refresh');
    localStorage.removeItem('prevenia_user');
    window.location.href = 'login.html';
  }

  get(path) { return this._request('GET', path); }
  post(path, body, isFormData) { return this._request('POST', path, body, isFormData); }
  patch(path, body, isFormData) { return this._request('PATCH', path, body, isFormData); }
  put(path, body) { return this._request('PUT', path, body); }
  del(path) { return this._request('DELETE', path); }

  // =============================================
  // AUTH
  // =============================================

  async login(email, password) {
    const data = await this.post('/auth/login/', { email, password });
    this._token = data.access;
    this._refreshToken = data.refresh;
    localStorage.setItem('prevenia_token', data.access);
    localStorage.setItem('prevenia_refresh', data.refresh);
    localStorage.setItem('prevenia_user', JSON.stringify(data.user));
    return data;
  }

  requestPasswordReset(email) {
    return this.post('/auth/password-reset/', { email });
  }

  confirmPasswordReset(uid, token, newPassword, passwordConfirm) {
    return this.post('/auth/password-reset/confirm/', {
      uid,
      token,
      new_password: newPassword,
      password_confirm: passwordConfirm,
    });
  }

  async logout() {
    try {
      await this.post('/auth/logout/', { refresh: this._refreshToken });
    } catch {}
    this._logout();
  }

  async register(payload) {
    const data = await this.post('/auth/register/', payload);
    this._token = data.access;
    this._refreshToken = data.refresh;
    localStorage.setItem('prevenia_token', data.access);
    localStorage.setItem('prevenia_refresh', data.refresh);
    localStorage.setItem('prevenia_user', JSON.stringify(data.user));
    return data;
  }

  getProfile() { return this.get('/auth/me/'); }
  updateProfile(data) { return this.patch('/auth/me/', data); }
  changePassword(oldPwd, newPwd) {
    return this.post('/auth/change-password/', { old_password: oldPwd, new_password: newPwd });
  }

  // =============================================
  // ATHLETES
  // =============================================

  getAthletes(params = {}) {
    const qs = new URLSearchParams(params).toString();
    return this.get(`/athletes/${qs ? '?' + qs : ''}`);
  }

  getAthlete(id) { return this.get(`/athletes/${id}/`); }

  createAthlete(payload) { return this.post('/athletes/', payload); }

  updateAthlete(id, payload) { return this.patch(`/athletes/${id}/`, payload); }

  deleteAthlete(id) { return this.del(`/athletes/${id}/`); }

  getAthleteAssessments(id) { return this.get(`/athletes/${id}/assessments/`); }

  getAthleteAlerts(id) { return this.get(`/athletes/${id}/alerts/`); }

  getRiskSummary() { return this.get('/athletes/risk-summary/'); }

  // =============================================
  // ASSESSMENTS
  // =============================================

  getAssessments(params = {}) {
    const qs = new URLSearchParams(params).toString();
    return this.get(`/assessments/${qs ? '?' + qs : ''}`);
  }

  getAssessment(id) { return this.get(`/assessments/${id}/`); }

  /**
   * Analyze image immediately (upload + analyze in one call)
   * @param {File} imageFile
   * @param {number} athleteId
   * @param {string} viewType - 'frontal'|'lateral'|'posterior'|'dynamic'
   * @param {string} exerciseType - general, squat, lunge, push_up, plank, side_plank, burpee,
   * jumping_jack, deadlift, glute_bridge, calf_raise, step_up, mountain_climber, overhead_press,
   * biceps_curl, row, triceps_dip, lateral_raise, crunch, jump_landing
   */
  async analyzeImage(imageFile, athleteId, viewType = 'frontal', exerciseType = 'general') {
    const formData = new FormData();
    formData.append('image', imageFile);
    formData.append('athlete_id', athleteId);
    formData.append('view_type', viewType);
    formData.append('exercise_type', exerciseType);
    return this.post('/assessments/analyze-image/', formData, true);
  }

  analyzePosePreview(imageFile, exerciseType = 'general', viewType = 'frontal') {
    const formData = new FormData();
    formData.append('image', imageFile);
    formData.append('exercise_type', exerciseType);
    formData.append('view_type', viewType);
    return this.post('/assessments/pose-preview/', formData, true);
  }

  analyzeExerciseSession(frames, athleteId, exerciseType, viewType, durationSeconds) {
    const formData = new FormData();
    frames.forEach(frame => formData.append('images', frame));
    formData.append('athlete_id', athleteId);
    formData.append('exercise_type', exerciseType);
    formData.append('view_type', viewType);
    formData.append('duration_seconds', String(durationSeconds));
    return this.post('/assessments/analyze-exercise-session/', formData, true);
  }

  saveBiomechanicalSession(payload) {
    const formData = new FormData();
    Object.entries(payload).forEach(([key, val]) => {
      if (val === undefined || val === null) return;
      if (key === 'image' && val instanceof Blob) {
        formData.append('image', val, val.name || 'biomechanics-session.jpg');
      } else if (typeof val === 'object') {
        formData.append(key, JSON.stringify(val));
      } else {
        formData.append(key, String(val));
      }
    });
    return this.post('/assessments/save-biomechanical-session/', formData, true);
  }

  saveDoctorReview(assessmentId, data) {
    return this.post(`/assessments/${assessmentId}/save-doctor-review/`, data);
  }

  getAthleteHistory(athleteId) {
    return this.get(`/assessments/athlete-history/?athlete_id=${athleteId}`);
  }

  /**
   * Trigger analysis on existing assessment with already-uploaded image
   */
  analyzeAssessment(id) {
    return this.post(`/assessments/${id}/analyze/`, {});
  }

  getAssessmentPDF(id) { return this._request('GET', `/assessments/${id}/pdf/`, null, false, 'blob'); }

  // =============================================
  // ALERTS
  // =============================================

  getAlerts(params = {}) {
    const qs = new URLSearchParams(params).toString();
    return this.get(`/assessments/alerts/${qs ? '?' + qs : ''}`);
  }

  resolveAlert(id, notes = '') {
    return this.post(`/assessments/alerts/${id}/resolve/`, { notes });
  }

  markAllAlertsRead() {
    return this.post('/assessments/alerts/mark-all-read/', {});
  }

  // =============================================
  // REPORTS
  // =============================================

  getDashboardStats() { return this.get('/reports/dashboard-stats/'); }

  generateReport(type, athleteId = null, dateFrom = null, dateTo = null) {
    return this.post('/reports/generate/', {
      report_type: type,
      athlete_id: athleteId,
      date_from: dateFrom,
      date_to: dateTo,
    });
  }

  getReports() { return this.get('/reports/'); }
  downloadReport(id) { return this.get(`/reports/${id}/download/`); }
}

// Singleton instance
const api = new PrevenIAClient();

// =============================================
// DEMO MODE HELPERS (when backend is not running)
// =============================================

const DEMO_MODE = window.location.protocol === 'file:' || window.location.hostname === 'localhost';

function getDemoStats() {
  return {
    athletes: { total: 247, risk_distribution: { low: 98, medium: 62, high: 70, critical: 17 }, average_risk_score: 42.3 },
    assessments: { today: 18, this_month: 143 },
    alerts: { active: 8, critical: 3, recent: [] },
    zone_frequency: { knee_left: 38, knee_right: 36, hip_left: 24, shoulder_left: 29, spine_lateral: 16 },
  };
}

// Export for use in other scripts
window.api = api;
window.DEMO_MODE = DEMO_MODE;
window.getDemoStats = getDemoStats;
