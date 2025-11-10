FROM wordpress:php8.3-fpm-alpine

# Install ssmtp for email sending
RUN apk add --no-cache ssmtp

# Configure ssmtp
RUN echo "mailhub=dell-workstation.tail67811d.ts.net:587" > /etc/ssmtp/ssmtp.conf && \
    echo "FromLineOverride=YES" >> /etc/ssmtp/ssmtp.conf && \
    echo "UseTLS=YES" >> /etc/ssmtp/ssmtp.conf && \
    echo "UseSTARTTLS=YES" >> /etc/ssmtp/ssmtp.conf && \
    echo "hostname=dell-workstation.tail67811d.ts.net" >> /etc/ssmtp/ssmtp.conf

# Create symbolic link for sendmail
RUN ln -sf /usr/sbin/ssmtp /usr/sbin/sendmail

# Copy custom entrypoint script
COPY docker-entrypoint-custom.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint-custom.sh

ENTRYPOINT ["docker-entrypoint-custom.sh"]
CMD ["php-fpm"]
