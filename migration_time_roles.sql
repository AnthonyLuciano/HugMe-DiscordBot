-- Migração para adicionar campos de cargos baseados no tempo de apoio
-- Execute este script no seu banco de dados MySQL

-- Adicionar coluna para cargo padrão de apoiador
ALTER TABLE guild_configs
ADD COLUMN cargo_apoiador_default VARCHAR(20) DEFAULT NULL;

-- Adicionar coluna para cargos baseados no tempo (JSON)
ALTER TABLE guild_configs
ADD COLUMN cargos_tempo JSON DEFAULT ('{}');

-- Verificar se as colunas foram adicionadas
DESCRIBE guild_configs;

-- Exemplo de como configurar cargos de tempo manualmente (opcional):
-- UPDATE guild_configs SET
--   cargo_apoiador_default = '123456789012345678',  -- ID do cargo padrão
--   cargos_tempo = '{
--     "30": "123456789012345679",   -- Cargo para 30+ dias
--     "90": "123456789012345680",   -- Cargo para 90+ dias
--     "180": "123456789012345681",  -- Cargo para 180+ dias
--     "365": "123456789012345682"   -- Cargo para 365+ dias
--   }'
-- WHERE guild_id = '123456789012345678';