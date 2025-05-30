import logging
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from mcp.server.fastmcp import FastMCP
import csv

logger = logging.getLogger('email_tools')

EMAIL_SENDER = os.environ.get("EMAIL_SENDER")
EMAIL_AUTHCODE = os.environ.get("EMAIL_AUTHCODE")

def register_email_tools(mcp: FastMCP):
    @mcp.tool()
    def send_email(
        recipient_email: str, 
        subject: str, 
        body: str,
        attachments: list = None
    ) -> dict:
        """
        发送邮件工具。
        参数：
        - recipient_email: 收件人邮箱
        - subject: 邮件主题
        - body: 邮件正文
        - attachments: 附件列表，每个附件是一个字典，包含：
            - path: 文件路径
            - filename: 文件名（可选，默认使用原文件名）
        返回：
        - 成功或失败的状态
        """
        logger.info(f"准备发送邮件到 {recipient_email}，主题：{subject}")

        try:
            # 创建邮件对象
            msg = MIMEMultipart()
            msg['From'] = EMAIL_SENDER
            msg['To'] = recipient_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))

            # 添加附件
            if attachments:
                for attachment in attachments:
                    file_path = attachment['path']
                    filename = attachment.get('filename', os.path.basename(file_path))
                    
                    # 检查文件是否存在
                    if not os.path.exists(file_path):
                        raise FileNotFoundError(f"附件文件不存在: {file_path}")
                    
                    # 读取文件并创建附件
                    with open(file_path, 'rb') as f:
                        part = MIMEApplication(f.read())
                        part.add_header(
                            'Content-Disposition',
                            'attachment',
                            filename=filename
                        )
                        msg.attach(part)
                    logger.info(f"已添加附件: {filename}")

            # 连接 QQ 邮箱的 SMTP 服务器并发送邮件
            with smtplib.SMTP_SSL('smtp.qq.com', 465) as server:
                server.login(EMAIL_SENDER, EMAIL_AUTHCODE)
                server.send_message(msg)
                server.quit()

            logger.info(f"邮件成功发送到 {recipient_email}")
            return {
                "success": True, 
                "result": "邮件发送成功",
                "attachments": [os.path.basename(att['path']) for att in (attachments or [])]
            }
        except Exception as e:
            logger.error(f"发送邮件失败: {e}")
            return {"success": False, "result": str(e)}

    @mcp.tool()
    def read_contacts_from_csv(csv_path: str) -> dict:
        """
        读取CSV格式的联系人文件。
        参数:
        - csv_path: 文件路径
        返回:
        - 联系人列表
        """
        try:
            contacts = []
            with open(csv_path, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    contacts.append({
                        "name": row.get("姓名") or row.get("name"),
                        "email": row.get("邮箱") or row.get("email"),
                        "phone": row.get("手机") or row.get("phone"),
                    })
            return {"success": True, "contacts": contacts}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @mcp.tool()
    def write_contacts_to_csv(csv_path: str, contacts: list, overwrite: bool = False) -> dict:
        """
        写入联系人到CSV文件。
        参数:
        - csv_path: 文件路径
        - contacts: 联系人列表，每个联系人是字典（name, email, phone）
        - overwrite: 是否覆盖原文件，默认False为追加
        返回:
        - 操作结果
        """
        try:
            file_exists = os.path.exists(csv_path)
            mode = 'w' if overwrite or not file_exists else 'a'
            fieldnames = ["姓名", "邮箱", "手机"]
            with open(csv_path, mode, newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                if mode == 'w' or not file_exists:
                    writer.writeheader()
                for contact in contacts:
                    writer.writerow({
                        "姓名": contact.get("name", ""),
                        "邮箱": contact.get("email", ""),
                        "手机": contact.get("phone", "")
                    })
            return {"success": True, "message": f"已写入{len(contacts)}个联系人到{csv_path}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

