# mt5-forward — MQL5専用・軽量版をベースにした薄いラッパ
# 設計: docs/application/mt5-forward/deployment.md §2
#
# ⚠️ 未テスト雛形: ベースイメージの拡張ポイント（init.d 相当 / s6 / supervisord）は実装時に
#    ベースイメージの README・構造を確認して合わせること（推測で entrypoint を上書きしない）。

# MQL5専用・軽量版（約600MB, Python不要）。latest は使わず固定タグ（再現性, operations.md §4）
FROM gmag11/metatrader5_vnc:1.1

# タイムゾーン UTC 固定（NF-005: ロールオーバー/週末フラット判定が時刻依存）
ENV TZ=UTC

# EA/インジ/テンプレは volume(ro) でマウントするため COPY しない（MT-007: 再ビルド不要差し替え）。
# 起動時に /artifacts の .ex5 配置 + CSV/ログ配線を行う初期化フックのみ追加する。
COPY entrypoint-hook.sh /opt/mt5-forward/entrypoint-hook.sh
RUN chmod +x /opt/mt5-forward/entrypoint-hook.sh

# ベースの起動シーケンス（KasmVNC + Wine）を壊さないよう、フックは
# ベースイメージの拡張ポイントへ登録する（完全置換しない）。具体的な登録先は実装時に確認:
#   例) s6-overlay なら /etc/cont-init.d/、custom-cont-init なら /custom-cont-init.d/ 等
# RUN ln -s /opt/mt5-forward/entrypoint-hook.sh /custom-cont-init.d/10-mt5-forward
