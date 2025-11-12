/**
 * Cloudflare Email Worker - Mailserver Inbound Relay
 *
 * メール受信 → Dell側APIに転送
 */

export default {
    async email(message, env, ctx) {
        const startTime = Date.now();

        try {
            // メール基本情報取得
            const from = message.from;
            const to = message.to;
            const subject = message.headers.get("subject") || "(件名なし)";

            console.log(`[INFO] メール受信: From=${from}, To=${to}, Subject=${subject}`);

            // メール本文を文字列に変換
            const rawEmail = await streamToString(message.raw);

            // Dell側APIに送信するデータ
            const emailData = {
                from: from,
                to: to,
                subject: subject,
                raw: rawEmail,
                timestamp: new Date().toISOString()
            };

            // Dell側APIにPOST
            const response = await fetch(env.DELL_API_ENDPOINT, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-API-Key": env.API_KEY,
                    "User-Agent": "Cloudflare-Email-Worker/1.0"
                },
                body: JSON.stringify(emailData),
                // 25秒タイムアウト（Worker制限30秒より短く）
                signal: AbortSignal.timeout(25000)
            });

            const elapsed = Date.now() - startTime;

            if (!response.ok) {
                const errorText = await response.text();
                console.error(`[ERROR] API応答エラー (${response.status}): ${errorText}, 経過時間=${elapsed}ms`);

                // 5xxエラー: 一時的エラーとして受信拒否（リトライされる）
                if (response.status >= 500) {
                    message.setReject(`Temporary API error: ${response.status}`);
                } else {
                    // 4xxエラー: 恒久的エラーとして受信拒否（リトライしない）
                    message.setReject(`Permanent API error: ${response.status}`);
                }
                return;
            }

            const result = await response.json();
            console.log(`[SUCCESS] メール転送成功: ${to}, 経過時間=${elapsed}ms, 結果=${JSON.stringify(result)}`);

        } catch (error) {
            const elapsed = Date.now() - startTime;
            console.error(`[ERROR] メール処理エラー: ${error.message}, 経過時間=${elapsed}ms`);

            // エラー時は一時的エラーとして受信拒否（送信者がリトライ）
            message.setReject(`Processing failed: ${error.message}`);
        }
    }
};

/**
 * ReadableStreamを文字列に変換
 */
async function streamToString(stream) {
    const chunks = [];
    const reader = stream.getReader();

    try {
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            chunks.push(value);
        }

        // Uint8Arrayを連結
        const totalLength = chunks.reduce((acc, chunk) => acc + chunk.length, 0);
        const result = new Uint8Array(totalLength);
        let offset = 0;

        for (const chunk of chunks) {
            result.set(chunk, offset);
            offset += chunk.length;
        }

        // UTF-8デコード
        return new TextDecoder('utf-8').decode(result);

    } finally {
        reader.releaseLock();
    }
}