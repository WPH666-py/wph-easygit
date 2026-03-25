#!/usr/bin/env python3
"""
easygit - 一个方便连接GitHub的Python脚本
实现GitHub仓库管理和文件操作功能
"""

import os
import sys
import json
import shutil
import subprocess
import webbrowser
import requests
from pathlib import Path
from urllib.parse import urlparse

class EasyGit:
    def __init__(self):
        self.config_file = Path.home() / ".easygit_config.json"
        self.config = self.load_config()
        self.github_api_base = "https://api.github.com"
        
    def load_config(self):
        """加载配置文件"""
        if self.config_file.exists():
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "github_token": "",
            "proxy": "",
            "repositories": {}
        }
    
    def save_config(self):
        """保存配置文件"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
    
    def get_github_headers(self):
        """获取GitHub API请求头"""
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "EasyGit/1.0"
        }
        if self.config.get("github_token"):
            headers["Authorization"] = f"token {self.config['github_token']}"
        return headers
    
    def make_github_request(self, endpoint, method="GET", data=None):
        """发送GitHub API请求"""
        url = f"{self.github_api_base}{endpoint}"
        headers = self.get_github_headers()
        
        proxies = {}
        if self.config.get("proxy"):
            proxies = {"https": self.config["proxy"]}
        
        try:
            if method == "GET":
                response = requests.get(url, headers=headers, proxies=proxies)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=data, proxies=proxies)
            elif method == "PUT":
                response = requests.put(url, headers=headers, json=data, proxies=proxies)
            elif method == "PATCH":
                response = requests.patch(url, headers=headers, json=data, proxies=proxies)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers, proxies=proxies)
            else:
                return False, "不支持的HTTP方法"
            
            if response.status_code in [200, 201, 204]:
                return True, response.json() if response.content else {}
            else:
                return False, f"GitHub API错误: {response.status_code} - {response.text}"
        except requests.exceptions.RequestException as e:
            return False, f"网络请求错误: {str(e)}"
    
    def git_add_spfd(self, repo_name):
        """添加仓库到配置（并尝试在GitHub上创建仓库）"""
        if repo_name in self.config["repositories"]:
            return False, f"仓库 '{repo_name}' 已存在"
        
        # 检查GitHub认证信息
        if not self.config.get("github_token") or not self.config.get("github_username"):
            return False, "请先配置GitHub用户名和Token"
        
        # 尝试在GitHub上创建仓库
        success, result = self.make_github_request(
            f"/user/repos",
            "POST",
            {
                "name": repo_name,
                "description": f"Repository created by EasyGit",
                "private": False  # 默认公开
            }
        )
        
        if success:
            # 创建成功，添加到配置
            self.config["repositories"][repo_name] = {
                "name": repo_name,
                "created_at": result.get("created_at", ""),
                "url": result.get("html_url", "")
            }
            self.save_config()
            return True, f"仓库 '{repo_name}' 创建并添加成功"
        else:
            # 如果创建失败，可能是仓库已存在，只添加到配置
            if "name already exists" in result or "Repository creation failed" in result:
                self.config["repositories"][repo_name] = {
                    "name": repo_name,
                    "created_at": "",
                    "url": f"https://github.com/{self.config['github_username']}/{repo_name}"
                }
                self.save_config()
                return True, f"仓库 '{repo_name}' 已存在，添加到配置成功"
            elif "Bad credentials" in result or "401" in str(result):
                return False, f"GitHub认证失败，请检查Token权限。需要'repo'权限才能创建仓库。"
            elif "403" in str(result):
                return False, f"权限不足，无法创建仓库。请确保Token有'repo'权限。"
            else:
                return False, f"创建仓库失败: {result}"
    
    def git_del_spfd(self, repo_name):
        """从配置中删除仓库（并尝试删除GitHub上的仓库）"""
        if repo_name not in self.config["repositories"]:
            return False, f"仓库 '{repo_name}' 不存在"
        
        # 检查GitHub认证信息
        if not self.config.get("github_token") or not self.config.get("github_username"):
            return False, "请先配置GitHub用户名和Token"
        
        # 尝试在GitHub上删除仓库
        success, result = self.make_github_request(
            f"/repos/{self.config['github_username']}/{repo_name}",
            "DELETE"
        )
        
        # 无论GitHub删除是否成功，都从本地配置中删除
        del self.config["repositories"][repo_name]
        self.save_config()
        
        if success:
            return True, f"仓库 '{repo_name}' 从GitHub和本地配置中删除成功"
        else:
            # GitHub删除失败，但本地已删除
            if "Not Found" in result:
                return True, f"仓库 '{repo_name}' 从本地配置中删除成功（GitHub上不存在）"
            elif "Bad credentials" in result or "401" in str(result):
                return False, f"GitHub认证失败，请检查Token权限。需要'repo'权限才能删除仓库。"
            elif "403" in str(result):
                return False, f"权限不足，无法删除仓库。请确保Token有'repo'权限且仓库属于您。"
            else:
                return True, f"仓库 '{repo_name}' 从本地配置中删除成功（GitHub删除失败: {result}）"
    
    def git_rnm_spfd(self, old_name, new_name):
        """重命名仓库（并尝试在GitHub上重命名）"""
        if old_name not in self.config["repositories"]:
            return False, f"仓库 '{old_name}' 不存在"
        
        if new_name in self.config["repositories"]:
            return False, f"仓库 '{new_name}' 已存在"
        
        # 检查GitHub认证信息
        if not self.config.get("github_token") or not self.config.get("github_username"):
            return False, "请先配置GitHub用户名和Token"
        
        # 尝试在GitHub上重命名仓库
        success, result = self.make_github_request(
            f"/repos/{self.config['github_username']}/{old_name}",
            "PATCH",
            {"name": new_name}
        )
        
        if success:
            # GitHub重命名成功，更新本地配置
            self.config["repositories"][new_name] = self.config["repositories"][old_name]
            self.config["repositories"][new_name]["name"] = new_name
            self.config["repositories"][new_name]["url"] = result.get("html_url", f"https://github.com/{self.config['github_username']}/{new_name}")
            del self.config["repositories"][old_name]
            self.save_config()
            return True, f"仓库 '{old_name}' 重命名为 '{new_name}'（GitHub同步成功）"
        else:
            # GitHub重命名失败，只更新本地配置
            if "name already exists" in result:
                return False, f"GitHub上已存在名为 '{new_name}' 的仓库"
            else:
                # 只更新本地配置
                self.config["repositories"][new_name] = self.config["repositories"][old_name]
                self.config["repositories"][new_name]["name"] = new_name
                self.config["repositories"][new_name]["url"] = f"https://github.com/{self.config['github_username']}/{new_name}"
                del self.config["repositories"][old_name]
                self.save_config()
                return True, f"仓库 '{old_name}' 重命名为 '{new_name}'（仅本地配置，GitHub重命名失败: {result}）"
    
    def git_up_spfd(self, file_path, repo_name):
        """上传文件到GitHub仓库"""
        if not os.path.exists(file_path):
            return False, f"文件或文件夹 '{file_path}' 不存在"
        
        if repo_name not in self.config["repositories"]:
            return False, f"仓库 '{repo_name}' 未配置"
        
        if not self.config.get("github_token"):
            return False, "请先配置GitHub Token"
        
        try:
            if os.path.isfile(file_path):
                return self.upload_file_to_github(file_path, repo_name)
            else:
                return self.upload_folder_to_github(file_path, repo_name)
        except Exception as e:
            return False, f"上传失败: {str(e)}"
    
    def upload_file_to_github(self, file_path, repo_name):
        """上传单个文件到GitHub"""
        with open(file_path, 'rb') as f:
            content = f.read()
        
        file_name = os.path.basename(file_path)
        
        # 将文件内容编码为base64
        import base64
        content_base64 = base64.b64encode(content).decode('utf-8')
        
        success, result = self.make_github_request(
            f"/repos/{self.config['github_username']}/{repo_name}/contents/{file_name}",
            "PUT",
            {
                "message": f"Upload {file_name}",
                "content": content_base64
            }
        )
        
        if success:
            return True, f"文件 '{file_name}' 上传成功"
        else:
            return False, result
    
    def upload_folder_to_github(self, folder_path, repo_name):
        """上传文件夹到GitHub"""
        folder_name = os.path.basename(folder_path)
        
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, folder_path)
                github_path = f"{folder_name}/{relative_path}"
                
                success, message = self.upload_file_to_github(file_path, repo_name)
                if not success:
                    return False, f"上传文件 '{file}' 失败: {message}"
        
        return True, f"文件夹 '{folder_name}' 上传成功"
    
    def git_pxy_web(self, proxy_url):
        """配置GitHub代理"""
        try:
            parsed = urlparse(proxy_url)
            if not parsed.scheme or not parsed.netloc:
                return False, "代理URL格式不正确"
            
            self.config["proxy"] = proxy_url
            self.save_config()
            return True, f"代理配置成功: {proxy_url}"
        except Exception as e:
            return False, f"代理配置失败: {str(e)}"
    
    def git_dn_spfd(self, repo_url, download_folder="下载的文件及文件夹"):
        """从GitHub下载仓库到指定文件夹"""
        # 如果参数是仓库名而不是URL，则转换为URL
        if '/' not in repo_url and not repo_url.startswith('http'):
            # 检查是否是已配置的仓库名
            if repo_url in self.config["repositories"]:
                if not self.config.get("github_username"):
                    return False, "请先配置GitHub用户名"
                repo_url = f"https://github.com/{self.config['github_username']}/{repo_url}.git"
            else:
                return False, f"仓库 '{repo_url}' 未配置"
        
        # 确保是有效的GitHub HTTPS URL
        if not repo_url.startswith('https://github.com/'):
            return False, "请输入有效的GitHub HTTPS地址"
        
        # 确保URL以.git结尾
        if not repo_url.endswith('.git'):
            repo_url += '.git'
        
        # 创建下载文件夹（如果不存在）
        if not os.path.exists(download_folder):
            try:
                os.makedirs(download_folder)
            except Exception as e:
                return False, f"创建下载文件夹失败: {str(e)}"
        
        # 提取仓库名作为文件夹名
        repo_name = repo_url.split('/')[-1].replace('.git', '')
        target_path = os.path.join(download_folder, repo_name)
        
        try:
            # 如果目标文件夹已存在，删除它
            if os.path.exists(target_path):
                shutil.rmtree(target_path)
            
            # 在下载文件夹中执行git clone
            result = subprocess.run(["git", "clone", repo_url, target_path], capture_output=True, text=True)
            if result.returncode == 0:
                return True, f"仓库 '{repo_name}' 下载到 '{download_folder}' 成功"
            else:
                return False, f"下载失败: {result.stderr}"
        except Exception as e:
            return False, f"下载失败: {str(e)}"
    
    def git_spfd_atrb(self, repo_name, attribute):
        """修改仓库属性（公开/私密）"""
        if repo_name not in self.config["repositories"]:
            return False, f"仓库 '{repo_name}' 未配置"
        
        if not self.config.get("github_token"):
            return False, "请先配置GitHub Token"
        
        if attribute == "pub/prv":
            private = True
            attr_text = "私密"
        elif attribute == "prv/pub":
            private = False
            attr_text = "公开"
        else:
            return False, "属性参数不正确，使用 'pub/prv' 或 'prv/pub'"
        
        success, result = self.make_github_request(
            f"/repos/{self.config['github_username']}/{repo_name}",
            "PATCH",
            {"private": private}
        )
        
        if success:
            return True, f"仓库 '{repo_name}' 已设置为{attr_text}"
        else:
            return False, result
    
    def git_rol_spfd(self, repo_name):
        """回滚仓库到上一版本"""
        if not os.path.exists(repo_name):
            return False, f"本地仓库 '{repo_name}' 不存在"
        
        try:
            os.chdir(repo_name)
            result = subprocess.run(["git", "reset", "--hard", "HEAD~1"], capture_output=True, text=True)
            os.chdir("..")
            
            if result.returncode == 0:
                return True, f"仓库 '{repo_name}' 回滚到上一版本成功"
            else:
                return False, f"回滚失败: {result.stderr}"
        except Exception as e:
            return False, f"回滚失败: {str(e)}"
    
    def git_rtn_spfd(self, repo_name):
        """还原仓库到最新版本"""
        if not os.path.exists(repo_name):
            return False, f"本地仓库 '{repo_name}' 不存在"
        
        try:
            os.chdir(repo_name)
            subprocess.run(["git", "fetch", "origin"], capture_output=True)
            result = subprocess.run(["git", "reset", "--hard", "origin/main"], capture_output=True, text=True)
            if result.returncode != 0:
                result = subprocess.run(["git", "reset", "--hard", "origin/master"], capture_output=True, text=True)
            os.chdir("..")
            
            if result.returncode == 0:
                return True, f"仓库 '{repo_name}' 还原到最新版本成功"
            else:
                return False, f"还原失败: {result.stderr}"
        except Exception as e:
            return False, f"还原失败: {str(e)}"
    
    def get_krn(self):
        """提供Karing下载地址"""
        karing_url = "https://karing.app/download/"
        
        message = f"Karing下载地址:\n{karing_url}"
        
        return True, message
    
    def get_krn_nd(self):
        """提供卡林海外服务器节点配置文件（稳连云）"""
        wl_url = "https://fn06.sp0303.xyz/#/plan/22"
        config_url = "https://vip17.stablec.top/s/d37f94b046d2ff9f88ff9f5e97260a58"
        
        message = f"""=== 卡林海外服务器节点配置文件（稳连云） ===

购买链接：{wl_url}

💳 价格：9.9元/月（130G流量最划算，支持微信支付）

📋 使用说明：
1. 访问购买链接：{wl_url}
2. 选择9.9元/月流量套餐（130G流量最划算）
3. 完成微信支付
4. 支付完成后，将以下代理配置文件复制到卡林的"添加配置-添加配置文件"中：
{config_url}

⚠️ 注意事项：
- 代理节点有有效期，过期后需要续费
- 续费请访问：{wl_url}
- 确保网络连接稳定，避免配置失败

稳联云 - 稳联相伴，网路更宽！"""
        
        return True, message
    
    def hub_log_rgs(self):
        """跳转到GitHub登录注册页面"""
        try:
            webbrowser.open("https://github.com/login")
            webbrowser.open("https://github.com/join")
            return True, "已打开GitHub登录和注册页面"
        except Exception as e:
            return False, f"打开浏览器失败: {str(e)}"
    
    def egit_cmd_menu(self):
        """显示所有指令菜单"""
        menu = """
=== EasyGit 指令菜单 ===

仓库管理:
  git-add-spfd:A          - 添加仓库A(默认项目公开)
  git-del-spfd:A          - 删除仓库A
  git-rnm-spfd:A,B        - 把仓库A重命名成仓库B
  git-spfd-atb:A,pub/prv - 把仓库A的属性从公开改为私密
  git-spfd-atb:A,prv/pub - 把仓库A的属性从私密改为公开

文件操作:
  git-up-spfd:B,A         - 把B文件或文件夹,通过其绝对路径上传到A仓库里
  git-dn-spfd:A           - 把GitHub仓库A,使用其https地址下载到本地文件夹"下载的文件及文件夹"中。"下载的文件及文件夹"若没有就会创建。
  git-rol-spfd:A          - 回滚仓库A里的项目到上一版本
  git-rtn-spfd:A          - 还原仓库A里的项目到最新版本

配置管理:
  git-pxy-web:C           - 配置git代理网址C
  cfg-hub-nmtok:A,B       - 绑定GitHub用户名和Token,每次使用需重新绑定,再次输入视为换绑。

工具功能:
  get-krn                 - 提供Karing下载地址
  get-krn-nd              - 提供卡林海外服务器节点配置文件（稳连云）
  hub-log-rgs             - 跳转到GitHub登录注册页面
  egit-author             - 查看作者信息
  egit-cmd-menu           - 显示所有指令菜单

使用说明:
  支持两种命令格式：
  - 冒号分隔: git-add-spfd:A 或 cfg-hub-nmtok:A,B
  - 空格分隔: git-add-spfd A 或 cfg-hub-nmtok A B
  
  使用前请先设置GitHub Token和用户名:
  - 使用 cfg-hub-nmtok:A,B ，每次打开页面请先绑定用户名和Token
  - 配置文件位置: ~/.easygit_config.json

权限说明:
  GitHub Token需要以下权限才能正常工作:
  - ✅ repo: 创建、删除、重命名仓库
  - ✅ public_repo: 操作公开仓库
  - ✅ 建议选择"repo"权限范围，包含所有仓库操作权限
  - ❌ 如果只有public_repo权限，无法删除或修改私有仓库

跨电脑使用说明:
  - 每台电脑都需要重新配置GitHub Token
  - Token权限必须包含"repo"才能删除仓库
  - 确保Token没有过期或被撤销
"""
        return True, menu
    
    def cfg_hub_nmtok(self, username, token):
        """绑定GitHub用户名和Token"""
        if not username or not token:
            return False, "用户名和Token不能为空"
        
        self.config["github_username"] = username
        self.config["github_token"] = token
        self.save_config()
        
        return True, f"GitHub认证信息绑定成功 - 用户名: {username}"
    
    def setup_github_auth(self):
        """设置GitHub认证信息（交互式）"""
        print("=== GitHub认证设置 ===")
        print("请按以下步骤操作：")
        print("1. 访问 https://github.com/settings/tokens")
        print("2. 点击 'Generate new token'")
        print("3. 选择 'repo' 权限范围")
        print("4. 生成Token并复制")
        print("5. 返回此界面输入用户名和Token")
        
        username = input("请输入GitHub用户名: ").strip()
        token = input("请输入GitHub Token: ").strip()
        
        if not username or not token:
            return False, "用户名和Token不能为空"
        
        self.config["github_username"] = username
        self.config["github_token"] = token
        self.save_config()
        
        return True, f"GitHub认证设置成功 - 用户名: {username}"
    
    def egit_author(self):
        """显示作者信息"""
        author_info = """
=== EasyGit 作者信息 ===

这个脚本专为新手连接GitHub而生，输入指令即可快速上手，欢迎各位大佬指正。

作者电话：18563982192，青岛理工大学2022级，你可以叫我水哥。

功能特点：
- 简单易用的GitHub操作指令
- 支持仓库管理、文件上传下载
- 支持代理配置和认证管理
- 专为新手设计，快速上手

感谢使用EasyGit！
"""
        return True, author_info
    
    def setup_github_auth(self):
        """设置GitHub认证信息"""
        print("=== GitHub认证设置 ===")
        
        token = input("请输入GitHub Personal Access Token: ").strip()
        if not token:
            return False, "Token不能为空"
        
        username = input("请输入GitHub用户名: ").strip()
        if not username:
            return False, "用户名不能为空"
        
        self.config["github_token"] = token
        self.config["github_username"] = username
        self.save_config()
        
        return True, "GitHub认证信息设置成功"

def execute_command(easygit, command_line):
    """执行单条命令"""
    command_line = command_line.strip()
    if not command_line:
        return True
    
    # 支持冒号分隔和空格分隔两种格式
    if ':' in command_line:
        # 冒号分隔格式: command:arg
        parts = command_line.split(':', 1)
        command = parts[0]
        args = [parts[1]] if len(parts) > 1 else []
    else:
        # 空格分隔格式: command arg
        parts = command_line.split()
        command = parts[0]
        args = parts[1:] if len(parts) > 1 else []
    
    try:
        if command == "git-add-spfd":
            if len(args) != 1:
                print("用法: git-add-spfd A (A为仓库名)")
                return True
            success, message = easygit.git_add_spfd(args[0])
        
        elif command == "git-del-spfd":
            if len(args) != 1:
                print("用法: git-del-spfd A (A为仓库名)")
                return True
            success, message = easygit.git_del_spfd(args[0])
        
        elif command == "git-rnm-spfd":
            if len(args) != 1:
                print("用法: git-rnm-spfd A/B (A为原仓库名，B为新仓库名)")
                return True
            parts = args[0].split('/')
            if len(parts) != 2:
                print("格式错误，使用: A/B")
                return True
            success, message = easygit.git_rnm_spfd(parts[0], parts[1])
        
        elif command == "git-up-spfd":
            if len(args) != 1:
                print("用法: git-up-spfd B,A (B为文件/文件夹路径，A为仓库名)")
                return True
            parts = args[0].split(',')
            if len(parts) != 2:
                print("格式错误，使用: B,A")
                return True
            success, message = easygit.git_up_spfd(parts[0], parts[1])
        
        elif command == "git-pxy-web":
            if len(args) != 1:
                print("用法: git-pxy-web C (C为代理网址)")
                return True
            success, message = easygit.git_pxy_web(args[0])
        
        elif command == "git-dn-spfd":
            if len(args) == 0:
                print("用法: git-dn-spfd A 或 git-dn-spfd A/B (A为仓库名或HTTPS地址，B为下载文件夹)")
                return True
            
            if len(args) == 1:
                # 单个参数：仓库名或HTTPS地址
                success, message = easygit.git_dn_spfd(args[0])
            else:
                # 两个参数：仓库名/HTTPS地址和下载文件夹
                success, message = easygit.git_dn_spfd(args[0], args[1])
        
        elif command == "git-spfd-atrb":
            if len(args) != 1:
                print("用法: git-spfd-atrb A,'pub/prv' 或 git-spfd-atrb A,'prv/pub'")
                return True
            parts = args[0].split(',')
            if len(parts) != 2:
                print("格式错误，使用: A,'pub/prv' 或 A,'prv/pub'")
                return True
            success, message = easygit.git_spfd_atrb(parts[0].strip("'"), parts[1].strip("'"))
        
        elif command == "git-rol-spfd":
            if len(args) != 1:
                print("用法: git-rol-spfd A (A为仓库名)")
                return True
            success, message = easygit.git_rol_spfd(args[0])
        
        elif command == "git-rtn-spfd":
            if len(args) != 1:
                print("用法: git-rtn-spfd A (A为仓库名)")
                return True
            success, message = easygit.git_rtn_spfd(args[0])
        
        elif command == "get-krn":
            success, message = easygit.get_krn()
        
        elif command == "get-krn-nd":
            success, message = easygit.get_krn_nd()
        
        elif command == "hub-log-rgs":
            success, message = easygit.hub_log_rgs()
        
        elif command == "egit-cmd-menu":
            success, message = easygit.egit_cmd_menu()
        
        elif command == "cfg-hub-nmtok":
            if len(args) != 1:
                print("用法: cfg-hub-nmtok A,B (A为GitHub用户名，B为Token)")
                return True
            parts = args[0].split(',')
            if len(parts) != 2:
                print("格式错误，使用: A,B")
                return True
            success, message = easygit.cfg_hub_nmtok(parts[0], parts[1])
        
        elif command == "egit-author":
            success, message = easygit.egit_author()
        
        elif command == "setup-auth":
            success, message = easygit.setup_github_auth()
        
        elif command == "exit" or command == "quit" or command == "0":
            print("退出EasyGit")
            return False
        
        else:
            print(f"未知命令: {command}")
            print("输入 'egit-cmd-menu' 查看所有可用命令")
            return True
        
        if success:
            print(f"✓ {message}")
        else:
            print(f"✗ {message}")
        return True
    
    except Exception as e:
        print(f"执行命令时发生错误: {str(e)}")
        return True

def main():
    """主函数"""
    easygit = EasyGit()
    
    # 如果有命令行参数，执行单条命令
    if len(sys.argv) > 1:
        command_line = ' '.join(sys.argv[1:])
        execute_command(easygit, command_line)
        return
    
    # 交互式模式
    print("=== EasyGit 交互式模式 ===")
    # 直接显示完整命令菜单
    success, menu_message = easygit.egit_cmd_menu()
    print(menu_message)
    print("输入 'exit'、'quit' 或 '0' 退出程序\n")
    
    while True:
        try:
            command_line = input("easygit> ").strip()
            if not command_line:
                continue
            
            if not execute_command(easygit, command_line):
                break
                
        except KeyboardInterrupt:
            print("\n退出EasyGit")
            break
        except EOFError:
            print("\n退出EasyGit")
            break

if __name__ == "__main__":
    main()