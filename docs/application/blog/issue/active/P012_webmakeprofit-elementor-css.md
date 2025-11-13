# P012: webmakeprofit.org Elementor CSS再生成失敗

**タイプ**: Problem  
**ステータス**: Open  
**優先度**: High  
**作成日**: 2025-11-13  
**担当**: 未割当

---

## 📋 課題概要
- `https://webmakeprofit.org/` のトップページでレイアウトが崩れ、フォントやボタン装飾が適用されない。
- ブラウザConsoleでは `wp-content/uploads/elementor/css/post-*.css` がすべてHTTP 404で失敗している。
- サーバー側でも `/mnt/backup-hdd/blog/sites/webmakeprofit/wp-content/uploads/elementor/css` が空ディレクトリになっており、Elementorが生成したCSSが存在しない。

## 🎯 目標
1. Elementorの外部CSSファイルを再生成して本番サイトの表示を元に戻す。  
2. 今後 `uploads/elementor/css` が自動的に消える / 書き込めなくなることを防ぐ。

## 📌 現状
- Playwright調査で以下の404を再現済み:
  - `https://webmakeprofit.org/wp-content/uploads/elementor/css/post-5.css?ver=1763019099`
  - `post-17.css`, `post-10878.css`, `post-13606.css` も全て同様に404。
- サーバー側ディレクトリの状態:
  ```bash
  $ ls -a /mnt/backup-hdd/blog/sites/webmakeprofit/wp-content/uploads/elementor/css
  .  ..
  $ stat -c '%a %U:%G' .../elementor/css
  755 system-admin:system-admin
  ```
- 所有者が `system-admin` (UID 1000)、パーミッションが755のため、PHP-FPM (www-data / UID 82) には書込権限がなく、ElementorがCSSファイルを生成できない。
- コンテナ初回起動時に `/var/www/html/.permissions-fixed` が作成される仕組みのため、新規ディレクトリ追加後も自動的にchownされない。

## 💡 想定される解決策
### 暫定対応
1. `sudo chown -R 82:82 /mnt/backup-hdd/blog/sites/webmakeprofit/wp-content/uploads/elementor/css`
2. `docker compose -f services/blog/docker-compose.yml exec wordpress wp --path=/var/www/html/webmakeprofit elementor flush_css`
3. ブラウザで `post-5.css` などがHTTP 200になること、フロントエンドのスタイルが戻ることを確認。

### 恒久対応案
- `docker-entrypoint-custom.sh` を修正し、 `/var/www/html` 以下で `www-data` 所有ではないディレクトリを起動毎に再chownする（または `.permissions-fixed` の仕組みを廃止）。
- 併せて `uploads` 配下を `find` で定期的に検査し、書込不可ディレクトリを検知する監視ジョブを追加。

## 📋 要件
- 書込権限の問題を根本的に解決し、Elementorが自動でCSSを再生成できること。
- 対応手順をRunbook化し、Phase A-2以降のドメイン移行時にも再利用できること。
- 影響範囲（他サイトのElementor CSS）を横展開で点検すること。

## 🚧 ブロッカー
- `chown` と `docker compose exec` にはroot / dockerグループ権限が必要。

## 📝 次のステップ
1. [ ] `uploads/elementor/css` の所有者を `www-data` に修正
2. [ ] Elementor CSS再生成 (`wp elementor flush_css`)
3. [ ] 再発防止のためのエントリポイント or 監視改善
4. [ ] 影響サイト洗い出し（他のドメインでも `elementor/css` が空か確認）

## 📚 関連ドキュメント
- `services/blog/docker-entrypoint-custom.sh` (パーミッション修正ロジック)
- `docs/application/blog/README.md`（既知のElementor課題一覧）
- `docs/application/blog/phases/phase-a2-production-domain-migration.md`（手順5: Elementorキャッシュクリア）

## 📅 更新履歴
- 2025-11-13: 調査結果をもとにIssue起票（Codex）
