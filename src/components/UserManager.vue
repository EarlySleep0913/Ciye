<script setup>
import { ref, onMounted } from 'vue'
import { Shield, ShieldOff, Trash2, Users, Loader2, UserPlus } from 'lucide-vue-next'

const props = defineProps({
  api: Function,
  showToast: Function,
  currentUser: Object,
})

const users = ref([])
const loading = ref(false)

// Add user form
const showAddForm = ref(false)
const newUsername = ref('')
const newPassword = ref('')
const newRole = ref('user')
const adding = ref(false)

async function loadUsers() {
  loading.value = true
  try {
    const data = await props.api('/api/users')
    users.value = data.users
  } catch (e) {
    props.showToast(e.message)
  } finally {
    loading.value = false
  }
}

async function addUser() {
  if (!newUsername.value.trim() || !newPassword.value.trim()) {
    props.showToast('请输入用户名和密码')
    return
  }
  adding.value = true
  try {
    await props.api('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({
        username: newUsername.value.trim(),
        password: newPassword.value.trim(),
      }),
    })
    // Set role if not default
    if (newRole.value === 'admin') {
      const data = await props.api('/api/users')
      const newUser = data.users.find(u => u.username === newUsername.value.trim())
      if (newUser) {
        await props.api('/api/users/role', {
          method: 'POST',
          body: JSON.stringify({ user_id: newUser.id, role: 'admin' }),
        })
      }
    }
    props.showToast(`用户 ${newUsername.value} 创建成功`)
    newUsername.value = ''
    newPassword.value = ''
    newRole.value = 'user'
    showAddForm.value = false
    await loadUsers()
  } catch (e) {
    props.showToast(e.message)
  } finally {
    adding.value = false
  }
}

async function toggleRole(user) {
  if (user.id === props.currentUser.id) {
    props.showToast('不能修改自己的角色')
    return
  }
  const newRole = user.role === 'admin' ? 'user' : 'admin'
  try {
    await props.api('/api/users/role', {
      method: 'POST',
      body: JSON.stringify({ user_id: user.id, role: newRole }),
    })
    user.role = newRole
    props.showToast(`已将 ${user.username} 设为${newRole === 'admin' ? '管理员' : '普通用户'}`)
  } catch (e) {
    props.showToast(e.message)
  }
}

async function deleteUser(user) {
  if (user.id === props.currentUser.id) {
    props.showToast('不能删除自己')
    return
  }
  if (!confirm(`确定要删除用户 "${user.username}" 吗？该操作不可恢复。`)) return
  try {
    await props.api(`/api/users/${user.id}/delete`, { method: 'POST' })
    users.value = users.value.filter(u => u.id !== user.id)
    props.showToast(`已删除用户 ${user.username}`)
  } catch (e) {
    props.showToast(e.message)
  }
}

onMounted(loadUsers)
</script>

<template>
  <article class="user-manager">
    <div class="um-header">
      <h3><Users :size="18" /> 用户管理</h3>
      <div class="um-actions">
        <button class="quiet-btn compact" @click="showAddForm = !showAddForm">
          <UserPlus :size="14" />
          {{ showAddForm ? '取消' : '添加用户' }}
        </button>
        <button class="quiet-btn compact" @click="loadUsers">
          <Loader2 v-if="loading" class="spin" :size="14" />
          刷新
        </button>
      </div>
    </div>

    <!-- Add User Form -->
    <div v-if="showAddForm" class="add-form">
      <div class="add-row">
        <input v-model="newUsername" placeholder="用户名" class="add-input" />
        <input v-model="newPassword" type="password" placeholder="密码" class="add-input" />
        <select v-model="newRole" class="add-select">
          <option value="user">普通用户</option>
          <option value="admin">管理员</option>
        </select>
        <button class="primary-btn compact" :disabled="adding" @click="addUser">
          <Loader2 v-if="adding" class="spin" :size="14" />
          <UserPlus v-else :size="14" />
          创建
        </button>
      </div>
    </div>

    <div class="user-table">
      <div class="user-row header-row">
        <span class="col-id">ID</span>
        <span class="col-name">用户名</span>
        <span class="col-role">角色</span>
        <span class="col-time">注册时间</span>
        <span class="col-actions">操作</span>
      </div>
      <div v-for="user in users" :key="user.id" class="user-row">
        <span class="col-id">{{ user.id }}</span>
        <span class="col-name">
          {{ user.username }}
          <span v-if="user.id === currentUser.id" class="badge-self">当前</span>
        </span>
        <span class="col-role">
          <span class="role-tag" :class="user.role">
            {{ user.role === 'admin' ? '管理员' : '用户' }}
          </span>
        </span>
        <span class="col-time">{{ user.created_at?.slice(0, 16) }}</span>
        <span class="col-actions">
          <button
            class="action-btn"
            :title="user.role === 'admin' ? '取消管理员' : '设为管理员'"
            :disabled="user.id === currentUser.id"
            @click="toggleRole(user)"
          >
            <ShieldOff v-if="user.role === 'admin'" :size="14" />
            <Shield v-else :size="14" />
          </button>
          <button
            class="action-btn danger"
            title="删除用户"
            :disabled="user.id === currentUser.id"
            @click="deleteUser(user)"
          >
            <Trash2 :size="14" />
          </button>
        </span>
      </div>
    </div>
  </article>
</template>

<style scoped>
.user-manager {
  border: 1px solid var(--line);
  background: rgba(255, 249, 236, 0.86);
  box-shadow: var(--shadow);
  padding: 24px;
}

.um-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.um-header h3 {
  font-size: 18px;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
}

.um-actions {
  display: flex;
  gap: 8px;
}

.add-form {
  margin-bottom: 16px;
  padding: 16px;
  background: rgba(255, 255, 255, 0.5);
  border: 1px solid var(--line);
  border-radius: 6px;
}

.add-row {
  display: flex;
  gap: 10px;
  align-items: center;
}

.add-input {
  flex: 1;
  height: 38px;
  padding: 0 12px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.6);
  color: var(--ink);
  font-family: var(--body-font);
  font-size: 14px;
  outline: none;
}

.add-input:focus {
  border-color: var(--gold);
}

.add-select {
  height: 38px;
  padding: 0 10px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.6);
  color: var(--ink);
  font-family: var(--body-font);
  font-size: 14px;
  outline: none;
}

.user-table {
  overflow-x: auto;
}

.user-row {
  display: grid;
  grid-template-columns: 40px 1fr 80px 140px 80px;
  gap: 12px;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid var(--line);
  font-size: 14px;
}

.header-row {
  font-size: 12px;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-bottom: 2px solid var(--line);
}

.col-id { text-align: center; color: var(--muted); }

.col-name {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 500;
}

.badge-self {
  font-size: 10px;
  padding: 1px 6px;
  background: var(--gold);
  color: white;
  border-radius: 8px;
  font-weight: 400;
}

.role-tag {
  font-size: 12px;
  padding: 2px 10px;
  border-radius: 10px;
  font-weight: 500;
}

.role-tag.admin {
  background: rgba(139, 58, 58, 0.1);
  color: var(--red);
}

.role-tag.user {
  background: rgba(111, 134, 111, 0.1);
  color: var(--sage);
}

.col-time {
  font-size: 13px;
  color: var(--muted);
}

.col-actions {
  display: flex;
  gap: 6px;
}

.action-btn {
  width: 30px;
  height: 30px;
  border: 1px solid var(--line);
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.5);
  color: var(--muted);
  display: grid;
  place-items: center;
  cursor: pointer;
  transition: all 160ms ease;
}

.action-btn:hover:not(:disabled) {
  color: var(--ink);
  border-color: var(--ink);
}

.action-btn.danger:hover:not(:disabled) {
  color: var(--red);
  border-color: var(--red);
  background: rgba(139, 58, 58, 0.05);
}

.action-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
.spin { animation: spin 900ms linear infinite; }
</style>
