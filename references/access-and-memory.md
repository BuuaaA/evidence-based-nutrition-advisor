# 数据库访问能力与记忆

仅在研究级流程确实需要受限数据库或全文时读取。

## 1. 不把身份等同于能力

分别判断：

- 本次任务是否需要发表级产物；
- 用户希望普通语言还是专业细节；
- 当前可访问哪些数据库和全文。

专业用户可能只需要个人决策，普通用户也可能持有机构导出文件。不要根据学历、职业或术语使用情况擅自扩大流程。

## 2. 轻量能力握手

仅在受限访问会实质影响下一步时询问一次：

> 这一步若要达到完整系统检索，需要 Embase/WoS/中文库或机构全文。你是否有可用的机构访问，或者更方便由我生成检索式、你导出 RIS/CSV 后继续？

如果用户已有可用记录，不重复询问；但开始使用外部登录会话前仍需遵守当前环境的授权要求。

## 3. 可以记忆的内容

经用户同意，可保存非敏感能力信息：

```yaml
research_access:
  pubmed: public
  embase: available | unavailable | unknown
  web_of_science: available | unavailable | unknown
  scopus: available | unavailable | unknown
  cnki: available | unavailable | unknown
  wanfang: available | unavailable | unknown
  vip: available | unavailable | unknown
  sinomed: available | unavailable | unknown
  institution: optional free text
  preferred_handoff: authenticated-browser | user-export | query-only
  last_verified: YYYY-MM
```

该记录只代表能力，不代表本次授权，也不证明会话仍有效。超过 6 个月或实际访问失败时重新确认。

## 4. 永不记忆或索取的内容

- 用户名、密码、验证码；
- Cookie、会话令牌、VPN 配置；
- API 密钥和下载令牌；
- 可用于冒充用户或绕过机构授权的信息。

用户应在浏览器或机构客户端中自行完成登录。Agent 只能在用户授权且当前环境允许的已认证会话中操作，或接收用户合法导出的 RIS/CSV/PDF。

## 5. 访问不足时的可交付方案

1. 生成逐库检索式，并明确哪些语法已实际核验；
2. 让用户在数据库中运行并导出 RIS/CSV；
3. 合并去重后继续筛选；
4. 通过合法开放获取、作者稿或用户提供文件获取全文；
5. 无法获得全文的研究标记为“待获取”，不得仅凭摘要完成正式数据提取或偏倚评价。

没有完成应有数据库和全文检索时，产物称为“初步/快速证据评估”，不能称为完整系统综述。

