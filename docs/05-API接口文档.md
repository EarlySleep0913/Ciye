# API 接口文档

## 基础信息

- Base URL：`http://127.0.0.1:8765`
- 认证方式：Bearer Token（Header: `Authorization: Bearer <token>`）
- Content-Type：`application/json; charset=utf-8`
- 错误响应：`{ "error": "错误信息" }`

---

## 认证接口

### POST /api/auth/login — 登录

**请求**：
```json
{ "username": "string", "password": "string" }
```

**响应**：
```json
{ "token": "uuid4-string", "user": { "id": 1, "username": "xxx", "role": "admin" } }
```

### POST /api/auth/register — 注册

**请求**：
```json
{ "username": "string", "password": "string" }
```

### GET /api/auth/me — 获取当前用户

**响应**：
```json
{ "id": 1, "username": "xxx", "role": "admin", "created_at": "2026-01-01T00:00:00" }
```

---

## 词书接口

### GET /api/books — 获取词书列表

**响应**：
```json
{
  "books": [
    {
      "id": 1, "name": "CET-4", "total": 500, "active": true,
      "new_count": 480, "learning_count": 15, "mastered_count": 5
    }
  ]
}
```

### POST /api/books — 创建词书

**请求**：
```json
{ "name": "词书名", "words": [{ "word": "apple", "translation": "苹果", ... }] }
```

**响应**：
```json
{ "id": 1, "inserted": 100 }
```

### POST /api/books/activate — 切换词书

**请求**：
```json
{ "book_id": 1, "daily_new_limit": 15 }
```

### POST /api/books/reset — 重置词书进度

**请求**：
```json
{ "book_id": 1 }
```

### GET /api/books/{id}/words — 获取词书单词（分页）

**参数**：`?page=1&per_page=50&query=apple`

### PUT /api/words/{id} — 编辑单词

### DELETE /api/words/{id} — 删除单词

### DELETE /api/books/{id} — 删除词书

---

## 学习接口

### GET /api/today — 获取今日词单

**响应**：
```json
{
  "reviews": [
    { "id": 1, "word": "apple", "translation": "苹果",
      "memory_strength": 1.5, "retention": 45.2, "taskType": "review" }
  ],
  "new_words": [
    { "id": 2, "word": "banana", "translation": "香蕉", "taskType": "new" }
  ],
  "daily_new_limit": 15, "active_book_id": 1
}
```

### POST /api/progress — 提交学习反馈

**请求**：
```json
{ "word_id": 1, "action": "known" }
```

**action 取值**：`forgot` / `vague` / `known` / `easy`

**响应**：
```json
{ "ok": true, "due_date": "2026-06-15", "status": "learning" }
```

### POST /api/reset-today — 重置今日学习

### POST /api/favorite — 收藏/取消收藏

**请求**：
```json
{ "word_id": 1, "favorite": true }
```

---

## 测试接口

### GET /api/test/words — 获取测试单词

**参数**：`?count=20`

### POST /api/test/check — 检查拼写

**请求**：
```json
{ "word_id": 1, "answer": "apple" }
```

---

## 错词/收藏

### GET /api/wrong-words — 错词列表

### POST /api/wrong-words/remove — 移除错词

### GET /api/favorites — 收藏列表

---

## 遗忘曲线

### GET /api/ebbinghaus — 总览

### GET /api/ebbinghaus/review — 待复习列表

### GET /api/ebbinghaus/word/{id} — 单词遗忘曲线详情

---

## 统计

### GET /api/stats — 学习统计

### GET /api/heatmap — 热力图数据

---

## 查词

### GET /api/lookup?word=apple — 查询单词

**响应**：
```json
{
  "word": "apple", "phonetic": "/ˈæp.əl/",
  "translation": "苹果", "definition": "A round fruit...",
  "example": "She ate an apple.", "audio_url": "...", "image_url": "..."
}
```

---

## AI 接口

### POST /api/ai/chat — AI 对话测试

**请求**：
```json
{ "message": "what is the difference?", "model": "deepseek-ai/DeepSeek-V4-Flash" }
```

### POST /api/ai/assistant — AI 助手对话

**请求**：
```json
{ "messages": [{ "role": "user", "content": "hello" }] }
```

内置 BingBing 英语教师 system prompt，使用 DeepSeek-V4-Flash。

### GET /api/ai/history — AI 助手对话历史

### POST /api/ai/import — AI 词书导入

**请求**：
```json
{ "text": "apple\nbanana" }
```
或
```json
{ "file": "base64...", "filename": "words.txt" }
```

### POST /api/ai/generate — AI 生成 CSV

### GET /api/ai/settings — 获取 AI 配置

### POST /api/ai/settings — 保存 AI 配置

---

## 用户管理（管理员）

### GET /api/users — 用户列表

### POST /api/users/role — 修改用户角色

### POST /api/users/{id}/delete — 删除用户

---

## 设置

### GET /api/settings — 获取设置

### POST /api/settings — 保存设置

### POST /api/pexels-key — 保存 Pexels Key

---

## 静态文件

### GET / — 首页

### GET /{filename} — 静态资源

支持：.html, .css, .js, .gif, .png, .jpg, .svg, .ico, .woff2
