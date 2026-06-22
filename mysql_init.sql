-- mysql_init.sql
-- Script unificado para crear la base de datos, el esquema y los datos iniciales de Academia Voley.
-- Importar este archivo en phpMyAdmin o MySQL Workbench.

CREATE DATABASE IF NOT EXISTS `academia_voley` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `academia_voley`;

-- Preparar importación limpia
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;
SET UNIQUE_CHECKS = 0;

DROP TABLE IF EXISTS `academia_voley`.`descargas_log`;
DROP TABLE IF EXISTS `academia_voley`.`logros`;
DROP TABLE IF EXISTS `academia_voley`.`solicitudes_equipo`;
DROP TABLE IF EXISTS `academia_voley`.`horarios_entrenador`;
DROP TABLE IF EXISTS `academia_voley`.`perfiles_jugadores`;
DROP TABLE IF EXISTS `academia_voley`.`asignacion_nutricion`;
DROP TABLE IF EXISTS `academia_voley`.`asignacion_entrenamientos`;
DROP TABLE IF EXISTS `academia_voley`.`nutricion`;
DROP TABLE IF EXISTS `academia_voley`.`entrenamientos`;
DROP TABLE IF EXISTS `academia_voley`.`galeria`;
DROP TABLE IF EXISTS `academia_voley`.`usuarios`;
DROP TABLE IF EXISTS `academia_voley`.`rol_permiso`;
DROP TABLE IF EXISTS `academia_voley`.`permisos`;
DROP TABLE IF EXISTS `academia_voley`.`roles`;

SET FOREIGN_KEY_CHECKS = 1;
SET UNIQUE_CHECKS = 1;

-- 1. Tabla de roles
CREATE TABLE IF NOT EXISTS `roles` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `nombre` VARCHAR(50) NOT NULL UNIQUE,
  `descripcion` VARCHAR(255) NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. Tabla de permisos
CREATE TABLE IF NOT EXISTS `permisos` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `nombre` VARCHAR(100) NOT NULL UNIQUE,
  `descripcion` VARCHAR(255) NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. Tabla pivot rol_permiso
CREATE TABLE IF NOT EXISTS `rol_permiso` (
  `rol_id` INT NOT NULL,
  `permiso_id` INT NOT NULL,
  PRIMARY KEY (`rol_id`, `permiso_id`),
  FOREIGN KEY (`rol_id`) REFERENCES `roles`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`permiso_id`) REFERENCES `permisos`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. Tabla de usuarios
CREATE TABLE IF NOT EXISTS `usuarios` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `nombre` VARCHAR(150) NOT NULL,
  `apellido` VARCHAR(150) NOT NULL,
  `email` VARCHAR(255) NOT NULL UNIQUE,
  `password` VARCHAR(255) NOT NULL,
  `rol` VARCHAR(50) NOT NULL DEFAULT 'jugador',
  `rol_id` INT NULL,
  `fecha_nacimiento` DATE DEFAULT NULL,
  `edad` INT DEFAULT NULL,
  `genero` VARCHAR(50) DEFAULT NULL,
  `cedula` VARCHAR(100) DEFAULT NULL,
  `descripcion` TEXT NULL,
  `link_facebook` VARCHAR(255) NULL,
  `link_instagram` VARCHAR(255) NULL,
  `last_activity` DATETIME DEFAULT NULL,
  `activo` TINYINT(1) NOT NULL DEFAULT 1,
  `idioma` VARCHAR(5) NOT NULL DEFAULT 'es',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`rol_id`) REFERENCES `roles`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. Galería
CREATE TABLE IF NOT EXISTS `galeria` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `titulo` VARCHAR(255),
  `descripcion` TEXT,
  `imagen_url` VARCHAR(512),
  `tipo` VARCHAR(50),
  `fecha_subida` DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. Entrenamientos
CREATE TABLE IF NOT EXISTS `entrenamientos` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `titulo` VARCHAR(255) NOT NULL,
  `descripcion` TEXT,
  `ejercicios` TEXT,
  `duracion_minutos` INT DEFAULT NULL,
  `dificultad` VARCHAR(50) DEFAULT NULL,
  `imagen_url` VARCHAR(512) DEFAULT NULL,
  `fecha_creacion` DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 7. Nutrición
CREATE TABLE IF NOT EXISTS `nutricion` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `titulo` VARCHAR(255) NOT NULL,
  `desayuno` TEXT,
  `almuerzo` TEXT,
  `cena` TEXT,
  `merienda` TEXT,
  `hidratacion` TEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 8. Asignaciones de entrenamientos y nutrición
CREATE TABLE IF NOT EXISTS `asignacion_entrenamientos` (
  `jugador_id` INT NOT NULL,
  `entrenamiento_id` INT NOT NULL,
  `completado` TINYINT(1) DEFAULT 0,
  PRIMARY KEY (`jugador_id`, `entrenamiento_id`),
  FOREIGN KEY (`jugador_id`) REFERENCES `usuarios`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`entrenamiento_id`) REFERENCES `entrenamientos`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `asignacion_nutricion` (
  `jugador_id` INT PRIMARY KEY,
  `nutricion_id` INT NOT NULL,
  FOREIGN KEY (`jugador_id`) REFERENCES `usuarios`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`nutricion_id`) REFERENCES `nutricion`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 9. Perfiles de jugadores
CREATE TABLE IF NOT EXISTS `perfiles_jugadores` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `usuario_id` INT NOT NULL,
  `altura_cm` INT DEFAULT NULL,
  `peso_kg` DECIMAL(5,2) DEFAULT NULL,
  `posicion` VARCHAR(100) DEFAULT NULL,
  `otros` TEXT,
  FOREIGN KEY (`usuario_id`) REFERENCES `usuarios`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 10. Horarios de entrenadores
CREATE TABLE IF NOT EXISTS `horarios_entrenador` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `entrenador_id` INT NOT NULL,
  `dias` VARCHAR(255) DEFAULT NULL,
  `horario` VARCHAR(255) DEFAULT NULL,
  `precio` VARCHAR(100) DEFAULT NULL,
  `descripcion` TEXT DEFAULT NULL,
  `creado_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`entrenador_id`) REFERENCES `usuarios`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 11. Solicitudes para unirse al equipo
CREATE TABLE IF NOT EXISTS `solicitudes_equipo` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `entrenador_id` INT NOT NULL,
  `nombre` VARCHAR(150) NOT NULL,
  `email` VARCHAR(255) NOT NULL,
  `telefono` VARCHAR(100) DEFAULT NULL,
  `mensaje` TEXT DEFAULT NULL,
  `tipo` VARCHAR(20) NOT NULL DEFAULT 'nuevo',
  `estado` VARCHAR(50) NOT NULL DEFAULT 'pendiente',
  `creado_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `actualizado_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (`entrenador_id`) REFERENCES `usuarios`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 12. Logros
CREATE TABLE IF NOT EXISTS `logros` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `titulo` VARCHAR(255) NOT NULL,
  `descripcion` TEXT,
  `fecha_logro` DATE,
  `usuario_id` INT DEFAULT NULL,
  `imagen_url` VARCHAR(255) DEFAULT NULL,
  FOREIGN KEY (`usuario_id`) REFERENCES `usuarios`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 13. Historial de descargas
CREATE TABLE IF NOT EXISTS `descargas_log` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `usuario_id` INT NOT NULL,
  `nombre_archivo` VARCHAR(255) NOT NULL,
  `fecha_descarga` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`usuario_id`) REFERENCES `usuarios`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Índices adicionales
CREATE INDEX IF NOT EXISTS `idx_usuarios_rol` ON `usuarios`(`rol`);
CREATE INDEX IF NOT EXISTS `idx_usuarios_rol_id` ON `usuarios`(`rol_id`);
CREATE INDEX IF NOT EXISTS `idx_galeria_tipo` ON `galeria`(`tipo`);

-- INSERCIÓN DE DATOS INICIALES Y CONFIGURACIÓN
-- Insertar Roles
INSERT IGNORE INTO `roles` (`nombre`, `descripcion`) VALUES
('super_usuario', 'Administrador Total con acceso global y de configuración'),
('entrenador', 'Entrenador con permisos del área deportiva y gestión de perfiles de jugadores'),
('jugador', 'Jugador de la academia que puede ver y completar sus entrenamientos');

-- Insertar Permisos
INSERT IGNORE INTO `permisos` (`nombre`, `descripcion`) VALUES
('modificar_entrenadores', 'Permiso para modificar datos de todos los entrenadores'),
('modificar_jugadores', 'Permiso para modificar datos de todos los jugadores'),
('gestionar_branding', 'Cambiar el logo de la academia, logos del sistema y logotipos de texto'),
('gestionar_staff', 'Agregar, editar o eliminar miembros del Staff'),
('editar_contenido_inicio', 'Editar cuadros de texto informativos de la Landing Page'),
('recomendar_rutinas', 'Recomendar rutinas de entrenamiento a los jugadores'),
('gestionar_perfil_deportivo', 'Completar y editar información técnica y física de jugadores'),
('recomendar_nutricion', 'Recomendar planes de nutrición'),
('editar_staff_propio', 'Editar información autorizada del propio perfil de staff');

-- Asociar permisos a roles (Super Usuario)
INSERT IGNORE INTO `rol_permiso` (`rol_id`, `permiso_id`)
SELECT r.id, p.id FROM `roles` r CROSS JOIN `permisos` p
WHERE r.nombre = 'super_usuario';

-- Asociar permisos a roles (Entrenador)
INSERT IGNORE INTO `rol_permiso` (`rol_id`, `permiso_id`)
SELECT r.id, p.id FROM `roles` r CROSS JOIN `permisos` p
WHERE r.nombre = 'entrenador' AND p.nombre IN (
  'recomendar_rutinas',
  'gestionar_perfil_deportivo',
  'recomendar_nutricion',
  'editar_staff_propio'
);

-- Superusuario inicial seguro
-- Correo: admin@academiavoley.net
-- Contraseña: AcaVoley!2026
INSERT IGNORE INTO `usuarios` (`nombre`, `apellido`, `email`, `password`, `rol`, `rol_id`)
VALUES (
  'Administrador',
  'Academia',
  'admin@academiavoley.net',
  '$2b$12$6BvRyFymHbmbc/oTVgG6he/zlYZH/cooI7TySlaAxJ5TgJ8pxaobO',
  'super_usuario',
  (SELECT id FROM `roles` WHERE nombre = 'super_usuario')
);

COMMIT;
