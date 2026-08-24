FROM php:8.2-apache

# Instalar extensiones necesarias
RUN docker-php-ext-install mysqli pdo_mysql

# Habilitar mod_rewrite
RUN a2enmod rewrite

# Establecer el directorio de trabajo
WORKDIR /var/www/html

# Copiar los archivos del frontend
COPY frontend/ /var/www/html/

# Configurar Apache para que use index.php como archivo predeterminado
RUN echo "DirectoryIndex index.php index.html" > /etc/apache2/conf-available/directory-index.conf \
    && a2enconf directory-index

# Configurar DocumentRoot explícitamente
RUN sed -i 's/DocumentRoot \/var\/www\/html/DocumentRoot \/var\/www\/html/g' /etc/apache2/sites-available/000-default.conf

# Dar permisos
RUN chown -R www-data:www-data /var/www/html && \
    chmod -R 755 /var/www/html

# Configurar PHP para mostrar errores (útil para debug)
RUN echo "display_errors = On" >> /usr/local/etc/php/conf.d/errors.ini && \
    echo "error_reporting = E_ALL" >> /usr/local/etc/php/conf.d/errors.ini

# Exponer el puerto 80
EXPOSE 80

# Iniciar Apache en primer plano
CMD ["apache2-foreground"]