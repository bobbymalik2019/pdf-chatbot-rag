import React, { useEffect, useState } from 'react';
import { Plus, RefreshCw, Users } from 'lucide-react';
import { authApi } from '../services/api.js';
export function UsersPage() {
  const [users, setUsers] = useState([]),
    [error, setError] = useState(''),
    [busy, setBusy] = useState(false),
    [open, setOpen] = useState(false);
  const [form, setForm] = useState({ display_name: '', email: '', password: '', roles: ['USER'] });
  async function refresh() {
    try {
      setUsers(await authApi.users());
      setError('');
    } catch (e) {
      setError(e.message);
    }
  }
  useEffect(() => {
    refresh();
  }, []);
  async function create(e) {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      await authApi.createUser(form);
      setOpen(false);
      setForm({ display_name: '', email: '', password: '', roles: ['USER'] });
      await refresh();
    } catch (ex) {
      setError(ex.message);
    } finally {
      setBusy(false);
    }
  }
  async function toggleRole(u) {
    const roles = u.roles.includes('ADMIN') ? ['USER'] : ['USER', 'ADMIN'];
    if (!window.confirm(`Change ${u.email} roles to ${roles.join(', ')}?`)) return;
    try {
      await authApi.changeRoles(u.id, roles);
      await refresh();
    } catch (ex) {
      setError(ex.message);
    }
  }
  return (
    <>
      <div className="page-heading flex">
        <div>
          <div className="eyebrow">ACCESS DIRECTORY</div>
          <h1>Users & roles</h1>
          <p>Provision accounts and assign application-wide roles.</p>
        </div>
        <button className="primary" onClick={() => setOpen((v) => !v)}>
          <Plus size={17} />
          New user
        </button>
      </div>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {open && (
        <form className="panel new-user" onSubmit={create}>
          <h3>Create user</h3>
          <div className="form-grid">
            <label>
              Display name
              <input
                required
                value={form.display_name}
                onChange={(e) => setForm({ ...form, display_name: e.target.value })}
              />
            </label>
            <label>
              Email
              <input
                type="email"
                required
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
              />
            </label>
            <label>
              Password (12+ characters)
              <input
                type="password"
                minLength={12}
                required
                autoComplete="new-password"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
              />
            </label>
            <label>
              Role
              <select
                value={form.roles.includes('ADMIN') ? 'ADMIN' : 'USER'}
                onChange={(e) =>
                  setForm({
                    ...form,
                    roles: e.target.value === 'ADMIN' ? ['ADMIN', 'USER'] : ['USER'],
                  })
                }
              >
                <option>USER</option>
                <option>ADMIN</option>
              </select>
            </label>
          </div>
          <div className="actions">
            <button type="button" className="secondary" onClick={() => setOpen(false)}>
              Cancel
            </button>
            <button disabled={busy} className="primary">
              {busy ? 'Creating…' : 'Create account'}
            </button>
          </div>
        </form>
      )}
      <div className="panel">
        <div className="table-header">
          <div>
            <Users size={19} />
            Directory <span className="count">{users.length}</span>
          </div>
          <button className="icon-btn" onClick={refresh} title="Refresh">
            <RefreshCw size={17} />
          </button>
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>IDENTITY</th>
                <th>ACCOUNT</th>
                <th>ROLES</th>
                <th>ACTIONS</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td>
                    <strong>{u.display_name}</strong>
                    <small>{u.email}</small>
                  </td>
                  <td>
                    <span className={`status ${u.is_active ? 'good' : 'bad'}`}>
                      {u.is_active ? 'Active' : 'Disabled'}
                    </span>
                  </td>
                  <td>
                    {u.roles.map((r) => (
                      <span className="role-pill" key={r}>
                        {r}
                      </span>
                    ))}
                  </td>
                  <td>
                    <button className="secondary small" onClick={() => toggleRole(u)}>
                      {u.roles.includes('ADMIN') ? 'Remove admin' : 'Make admin'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {users.length === 0 && <p className="empty">No users found</p>}
        </div>
      </div>
    </>
  );
}
