const IMAGE_EXTS = new Set(["png", "jpg", "jpeg", "webp", "gif"]);

export function normalizeAttachmentExt(ext?: string, url?: string): string {
  let normalized = (ext || "").toLowerCase().replace(/^\./, "");
  if (!normalized && url) {
    const path = url.split("?")[0] || "";
    const segment = path.split("/").pop() || "";
    const dot = segment.lastIndexOf(".");
    normalized = dot >= 0 ? segment.slice(dot + 1).toLowerCase() : "";
  }
  return normalized;
}

export function isImageAttachment(file: {
  ext?: string;
  url?: string;
}): boolean {
  return IMAGE_EXTS.has(normalizeAttachmentExt(file.ext, file.url));
}

/** 输入框/气泡内图片缩略图 URL（本地上传 vs 服务器文件） */
export function getAttachmentPreviewUrl(file: {
  url?: string;
  type?: string;
  ext?: string;
}): string | null {
  if (!file.url || !isImageAttachment(file)) return null;
  if (/^https?:\/\//.test(file.url)) return file.url;
  // 历史公共静态托管（兼容旧消息）
  if (file.url.startsWith("/static/uploads/")) return file.url;
  if (file.url.startsWith("/api/")) return file.url;
  // 用户私有 uploads / 工作空间路径：走鉴权预览 API
  return `/api/v1/chat/fs/preview?path=${encodeURIComponent(file.url)}`;
}

/** 附件在服务器上的绝对路径（供 AI 上下文与工具使用） */
export function getServerAttachmentPath(file: {
  type?: string;
  url?: string;
  filename?: string;
}): string {
  if (file.type === "skill") {
    return `/app/data/skills/${file.url}/SKILL.md`;
  }
  if (file.type === "local_file" || file.type === "local_dir") {
    return file.url || "";
  }
  const url = file.url || "";
  if (url.startsWith("/static/uploads/")) {
    const fileName = url.split("/").filter(Boolean).pop() || file.filename || "";
    return `/app/data/uploads/${fileName}`;
  }
  if (url && !url.startsWith("http")) {
    return url;
  }
  const fileName = url.split("/").filter(Boolean).pop() || file.filename || "";
  return `/app/data/uploads/${fileName}`;
}
