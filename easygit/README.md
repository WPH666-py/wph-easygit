# EasyGit - GitHub连接工具

EasyGit是一个用Python编写的方便连接GitHub的脚本工具，支持多种GitHub操作功能。

## 功能特性

- ✅ 仓库管理（添加、删除、重命名）
- ✅ 文件上传/下载
- ✅ 仓库属性管理（公开/私密）
- ✅ 版本回滚和还原
- ✅ 代理配置支持
- ✅ GitHub认证管理
- ✅ 命令菜单显示

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

### 1. 设置GitHub认证

首次使用前需要设置GitHub认证信息：

```bash
python easygit.py setup-auth
```

按照提示输入：
- GitHub Personal Access Token
- GitHub用户名

### 2. 查看所有命令

```bash
python easygit.py egit-cmd-menu
```

### 3. 常用命令示例

#### 仓库管理
```bash
# 添加仓库
python easygit.py git-add-spfd:myrepo

# 删除仓库
python easygit.py git-del-spfd:myrepo

# 重命名仓库
python easygit.py git-rnm-spfd:oldrepo/newrepo

# 修改仓库属性
python easygit.py git-spfd-atrb:myrepo,'pub/prv'  # 公开改为私密
python easygit.py git-spfd-atrb:myrepo,'prv/pub'  # 私密改为公开
```

#### 文件操作
```bash
# 上传文件到仓库
python easygit.py git-up-spfd:myfile.txt/myrepo

# 上传文件夹到仓库
python easygit.py git-up-spfd:myfolder/myrepo

# 下载仓库
python easygit.py git-dn-spfd:myrepo

# 回滚到上一版本
python easygit.py git-rol-spfd:myrepo

# 还原到最新版本
python easygit.py git-rtn-spfd:myrepo
```

#### 配置管理
```bash
# 配置代理
python easygit.py git-pxy-web:http://proxy.example.com:8080
```

#### 工具功能
```bash
# 获取Karing下载地址
python easygit.py get-krn

# 获取Karing海外服务器配置
python easygit.py get-krn-outsvr

# 打开GitHub登录页面
python easygit.py hub-log-rgs
```

## 配置文件

EasyGit的配置文件位于：`~/.easygit_config.json`

配置文件结构：
```json
{
  "github_token": "your_github_token",
  "github_username": "your_username",
  "proxy": "http://proxy.example.com:8080",
  "repositories": {
    "repo1": {
      "name": "repo1",
      "created_at": "",
      "url": ""
    }
  }
}
```

## 注意事项

1. **GitHub Token权限**：确保你的GitHub Personal Access Token具有以下权限：
   - `repo`（完全控制私有仓库）
   - `workflow`（可选，如果需要工作流功能）

2. **代理配置**：如果需要使用代理，请确保代理服务器支持HTTPS连接。

3. **文件路径**：上传文件时使用相对路径或绝对路径。

4. **仓库要求**：操作仓库前需要先在GitHub上创建对应的仓库。

## 错误处理

- 如果命令执行失败，会显示错误信息
- 网络错误会自动重试
- 配置错误会提示重新设置

## 许可证

MIT License