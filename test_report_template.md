# 测试报告模板

## 测试报告

**项目名称**: FastAPI + SQLAlchemy + SQLite + JWT + pytest 测试套件

**生成时间**: {timestamp}

---

## 一、测试摘要

| 指标 | 数值 |
|------|------|
| 测试用例总数 | {total_tests} |
| 通过用例数 | {passed_tests} |
| 失败用例数 | {failed_tests} |
| 跳过用例数 | {skipped_tests} |
| 通过率 | {pass_rate}% |
| 代码覆盖率 | {coverage}% |

---

## 二、测试模块详情

### 2.1 CRUD 单元测试 (test_crud_users.py)

| 测试类 | 测试数量 | 覆盖场景 |
|--------|----------|----------|
| TestGetUser | 4 | 正常查询、不存在用户、负ID、零ID |
| TestGetUserByEmail | 4 | 正常查询、不存在、空字符串、非法格式 |
| TestGetUsers | 5 | 正常列表、空库、分页、超限跳过 |
| TestGetUserByLogin | 4 | 登录成功、错误邮箱、错误密码、空凭据 |
| TestCreateUser | 4 | 创建成功、密码哈希、无@邮箱、默认值 |
| TestDeleteUser | 4 | 删除成功、不存在、重复删除、负ID |
| TestUpdateUser | 3 | 更新成功、不存在、部分更新 |
| TestUpdateUserPassword | 4 | 改密成功、旧密码错误、用户不存在、验证旧密码 |
| TestPasswordHash | 5 | 哈希生成、验证正确、验证错误、唯一性、空密码 |

### 2.2 路由集成测试 (test_routers_users.py)

| 测试类 | 测试数量 | 覆盖场景 |
|--------|----------|----------|
| TestCreateUser | 6 | 200/400/422 状态码、重复邮箱、缺失字段 |
| TestReadUsers | 5 | 管理员访问、普通用户拒绝、未授权、分页 |
| TestReadUserMe | 3 | 成功获取、未授权、未激活用户 |
| TestReadUserById | 6 | 本人/管理员/他人访问、404/403/401 |
| TestDeleteUser | 6 | 本人/管理员删除、权限拒绝、404 |
| TestUpdateUser | 6 | 本人/管理员更新、角色限制、404/403 |
| TestUpdateUserPassword | 6 | 改密成功、旧密码错误、禁止改他人密码 |
| TestAuthenticationScenarios | 5 | 过期/无效/无Token、格式错误 |

### 2.3 认证模块测试 (test_auth.py)

| 测试类 | 测试数量 | 覆盖场景 |
|--------|----------|----------|
| TestCreateAccessToken | 4 | 默认过期、自定义过期、数据正确、未来过期 |
| TestVerifyToken | 6 | 有效/无效/过期Token、错误密钥、缺失声明 |
| TestActiveUserCheck | 2 | 激活用户访问、未激活用户阻止 |
| TestRoleCheck | 2 | 管理员访问、普通用户拒绝 |
| TestLoginEndpoint | 7 | 登录成功/失败、缺失字段、空凭据 |
| TestTokenExpiry | 2 | 过期时间验证、有效期内可用 |
| TestRateLimiting | 1 | 高频请求限流 |
| TestTokenFormat | 2 | JWT格式验证、可解码验证 |
| TestEdgeCases | 3 | 无Bearer前缀、小写bearer、多Token |

---

## 三、权限测试覆盖

| 权限场景 | 测试覆盖 |
|----------|----------|
| 公开接口 | 创建用户 |
| 仅管理员 | 获取所有用户列表 |
| 仅本人 | 获取个人信息、修改密码 |
| 本人+管理员 | 查询用户、删除用户、更新用户 |

---

## 四、HTTP状态码覆盖

| 状态码 | 测试场景 |
|--------|----------|
| 200 | 所有成功操作 |
| 400 | 邮箱已注册、未激活用户 |
| 401 | 无Token、无效Token、过期Token、登录失败 |
| 403 | 权限不足、旧密码错误 |
| 404 | 用户不存在 |
| 422 | 请求参数验证失败 |
| 429 | 请求频率超限 |

---

## 五、覆盖率报告

```
{coverage_report}
```

---

## 六、运行命令

```bash
# 运行所有测试
python run_tests.py

# 运行带覆盖率的测试
pytest --cov=. --cov-report=html --cov-report=term-missing tests/

# 运行特定测试文件
pytest tests/test_crud_users.py -v

# 运行特定测试类
pytest tests/test_crud_users.py::TestCreateUser -v

# 运行特定测试方法
pytest tests/test_crud_users.py::TestCreateUser::test_create_user_success -v

# 生成测试报告
python run_tests.py report
```

---

## 七、改进建议

1. **增加边界测试**: 添加更多边界值测试用例
2. **并发测试**: 添加并发请求测试场景
3. **性能测试**: 添加API响应时间测试
4. **安全测试**: 添加SQL注入、XSS等安全测试
5. **集成测试**: 添加端到端业务流程测试

---

*报告由测试框架自动生成*
