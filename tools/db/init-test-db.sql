-- Separate database for the test suite.
--
-- The suite truncates tables wholesale between tests. Sharing a database with the
-- running application means every test run silently destroys the demo data — which is
-- exactly what happened before this existed.
CREATE DATABASE taxos_test OWNER taxos;
