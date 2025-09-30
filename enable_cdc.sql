-- Enable Change Data Feed (CDC) on the aspect_sentiment table
-- This is required for Databricks Vector Search to track changes

-- Enable CDC on the main table
ALTER TABLE main.ashwinpo_bloomin.aspect_sentiment 
SET TBLPROPERTIES (delta.enableChangeDataFeed = true);

-- Verify CDC is enabled
SHOW TBLPROPERTIES main.ashwinpo_bloomin.aspect_sentiment;

-- Check that the property is set correctly
SELECT 'Change Data Feed Status:' as info, 
       CASE WHEN EXISTS (
         SELECT 1 FROM (SHOW TBLPROPERTIES main.ashwinpo_bloomin.aspect_sentiment)
         WHERE key = 'delta.enableChangeDataFeed' AND value = 'true'
       ) THEN 'ENABLED ✅' 
       ELSE 'NOT ENABLED ❌' 
       END as status;

-- Optional: Check table history to see the CDC enablement
DESCRIBE HISTORY main.ashwinpo_bloomin.aspect_sentiment LIMIT 5;
