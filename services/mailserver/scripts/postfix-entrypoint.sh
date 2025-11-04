#!/bin/sh
set -eu

TEMPLATE_PATH="/etc/postfix/custom/main.cf.tmpl"
OUTPUT_PATH="/etc/postfix/main.cf"
CUSTOM_DIR="/etc/postfix/custom"

require_var() {
  VAR_NAME="$1"
  VAR_VALUE="$(eval "printf '%s' \"\${$VAR_NAME-}\"")"
  if [ -z "$VAR_VALUE" ]; then
    echo "ERROR: environment variable $VAR_NAME is required but not set." >&2
    exit 1
  fi
}

require_var "MAIL_DOMAIN"
require_var "MAIL_HOSTNAME"

MAIL_ADDITIONAL_DOMAINS="${MAIL_ADDITIONAL_DOMAINS:-}"
POSTFIX_TLS_CERT_FILE="${POSTFIX_TLS_CERT_FILE:-/var/lib/tailscale/certs/tls.crt}"
POSTFIX_TLS_KEY_FILE="${POSTFIX_TLS_KEY_FILE:-/var/lib/tailscale/certs/tls.key}"
POSTFIX_RELAYHOST="${POSTFIX_RELAYHOST:-[smtp.sendgrid.net]:587}"
POSTFIX_MESSAGE_SIZE_LIMIT="${POSTFIX_MESSAGE_SIZE_LIMIT:-26214400}"

if [ ! -f "$TEMPLATE_PATH" ]; then
  echo "ERROR: Postfix template not found at $TEMPLATE_PATH" >&2
  exit 1
fi

if [ ! -f "$POSTFIX_TLS_CERT_FILE" ] || [ ! -f "$POSTFIX_TLS_KEY_FILE" ]; then
  echo "WARNING: TLS certificate or key not found (${POSTFIX_TLS_CERT_FILE}, ${POSTFIX_TLS_KEY_FILE}). Postfix will start but TLS may fail." >&2
fi

# Compose virtual mailbox domain list.
VIRTUAL_MAILBOX_DOMAINS="$MAIL_DOMAIN"
if [ -n "$MAIL_ADDITIONAL_DOMAINS" ]; then
  # Transform whitespace/semicolon separated values into comma list.
  EXTRA_DOMAINS="$(printf '%s\n' "$MAIL_ADDITIONAL_DOMAINS" | tr ' ' '\n' | tr ',' '\n' | sed '/^$/d' | sort -u | paste -sd, -)"
  if [ -n "$EXTRA_DOMAINS" ]; then
    VIRTUAL_MAILBOX_DOMAINS="${VIRTUAL_MAILBOX_DOMAINS}, ${EXTRA_DOMAINS}"
  fi
fi

# Render main.cf from template.
awk \
  -v MAIL_DOMAIN="$MAIL_DOMAIN" \
  -v MAIL_HOSTNAME="$MAIL_HOSTNAME" \
  -v VIRTUAL_MAILBOX_DOMAINS="$VIRTUAL_MAILBOX_DOMAINS" \
  -v POSTFIX_TLS_CERT_FILE="$POSTFIX_TLS_CERT_FILE" \
  -v POSTFIX_TLS_KEY_FILE="$POSTFIX_TLS_KEY_FILE" \
  -v POSTFIX_RELAYHOST="$POSTFIX_RELAYHOST" \
  -v POSTFIX_MESSAGE_SIZE_LIMIT="$POSTFIX_MESSAGE_SIZE_LIMIT" \
  '{
    gsub("{{MAIL_DOMAIN}}", MAIL_DOMAIN);
    gsub("{{MAIL_HOSTNAME}}", MAIL_HOSTNAME);
    gsub("{{VIRTUAL_MAILBOX_DOMAINS}}", VIRTUAL_MAILBOX_DOMAINS);
    gsub("{{POSTFIX_TLS_CERT_FILE}}", POSTFIX_TLS_CERT_FILE);
    gsub("{{POSTFIX_TLS_KEY_FILE}}", POSTFIX_TLS_KEY_FILE);
    gsub("{{POSTFIX_RELAYHOST}}", POSTFIX_RELAYHOST);
    gsub("{{POSTFIX_MESSAGE_SIZE_LIMIT}}", POSTFIX_MESSAGE_SIZE_LIMIT);
    print;
  }' "$TEMPLATE_PATH" > "$OUTPUT_PATH"

chmod 640 "$OUTPUT_PATH"

# Synchronise SASL credentials into Postfix path.
if [ -f "${CUSTOM_DIR}/sasl_passwd" ]; then
  cp "${CUSTOM_DIR}/sasl_passwd" /etc/postfix/sasl_passwd
  chmod 600 /etc/postfix/sasl_passwd
  postmap /etc/postfix/sasl_passwd
else
  echo "WARNING: SASL credential file ${CUSTOM_DIR}/sasl_passwd not found. Outbound mail may fail." >&2
fi

# Ensure submissionポート向けのSASL/TLS設定を強制
postconf -e 'smtpd_relay_restrictions=permit_mynetworks,permit_sasl_authenticated,defer_unauth_destination'
postconf -e 'smtpd_sasl_type=dovecot'
postconf -e 'smtpd_sasl_path=private/auth'
postconf -e 'smtpd_sasl_auth_enable=yes'
postconf -e 'smtpd_tls_security_level=encrypt'

# Ensure log files exist and rsyslog is running so logs persist to mounted volume.
mkdir -p /var/log
touch /var/log/mail.log /var/log/mail.err /var/log/mail.warn
chmod 644 /var/log/mail.log /var/log/mail.err /var/log/mail.warn
cat <<'EOF' >/etc/rsyslog.d/50-postfix-file.conf
mail.*                         /var/log/mail.log
mail.err                       /var/log/mail.err
mail.warning                   /var/log/mail.warn
EOF
/usr/sbin/rsyslogd || {
  echo "WARNING: failed to start rsyslogd; Postfix logs may not be captured." >&2
}

# Ensure necessary directories exist with correct permissions.
chown -R root:root /etc/postfix

echo "Postfix configuration rendered to ${OUTPUT_PATH}."
echo "Starting Postfix in foreground..."

exec /usr/sbin/postfix start-fg
