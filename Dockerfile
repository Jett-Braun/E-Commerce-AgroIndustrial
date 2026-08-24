FROM php:8.2-apache

# Instalar extensiones necesarias
RUN docker-php-ext-install mysqli pdo_mysql

# Habilitar mod_rewrite
RUN a2enmod rewrite

# Copiar los archivos del frontend al contenedor
COPY frontend/ /var/www/html/

# Dar permisos
RUN chown -R www-data:www-data /var/www/html && \
    chmod -R 755 /var/www/html

# Exponer el puerto 80
EXPOSE 80

# Iniciar Apache
CMD ["apache2-foreground"]