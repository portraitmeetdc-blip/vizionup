-- Vizion Income — Supabase Schema
-- Run this in the Supabase SQL Editor to set up your database

-- Families table: each family is an isolated group
CREATE TABLE IF NOT EXISTS families (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    invite_code TEXT UNIQUE DEFAULT substr(md5(random()::text), 1, 8),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Profiles table: extends Supabase auth.users with app-specific data
CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    family_id UUID REFERENCES families(id) ON DELETE SET NULL,
    display_name TEXT NOT NULL,
    role TEXT DEFAULT '',
    avatar_url TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Holdings table: per-user stock positions
CREATE TABLE IF NOT EXISTS holdings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    ticker TEXT NOT NULL,
    shares NUMERIC NOT NULL,
    avg_cost NUMERIC NOT NULL,
    notes TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id, ticker)
);

-- Watchlist table: stocks a user is tracking
CREATE TABLE IF NOT EXISTS watchlist (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    ticker TEXT NOT NULL,
    target_price NUMERIC,
    notes TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id, ticker)
);

-- Row Level Security: users can only access their own data and family data

ALTER TABLE families ENABLE ROW LEVEL SECURITY;
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE holdings ENABLE ROW LEVEL SECURITY;
ALTER TABLE watchlist ENABLE ROW LEVEL SECURITY;

-- Profiles: users can read/update their own profile
CREATE POLICY "Users can view own profile"
    ON profiles FOR SELECT
    USING (auth.uid() = id);

CREATE POLICY "Users can update own profile"
    ON profiles FOR UPDATE
    USING (auth.uid() = id);

CREATE POLICY "Users can insert own profile"
    ON profiles FOR INSERT
    WITH CHECK (auth.uid() = id);

-- Profiles: users can view family members' profiles
CREATE POLICY "Users can view family members"
    ON profiles FOR SELECT
    USING (
        family_id IN (
            SELECT family_id FROM profiles WHERE id = auth.uid()
        )
    );

-- Families: members can view their family
CREATE POLICY "Members can view their family"
    ON families FOR SELECT
    USING (
        id IN (SELECT family_id FROM profiles WHERE id = auth.uid())
    );

-- Families: anyone authenticated can create a family
CREATE POLICY "Authenticated users can create families"
    ON families FOR INSERT
    WITH CHECK (auth.role() = 'authenticated');

-- Holdings: users can manage their own holdings
CREATE POLICY "Users can manage own holdings"
    ON holdings FOR ALL
    USING (user_id = auth.uid());

-- Holdings: users can view family members' holdings (read-only)
CREATE POLICY "Users can view family holdings"
    ON holdings FOR SELECT
    USING (
        user_id IN (
            SELECT id FROM profiles
            WHERE family_id = (SELECT family_id FROM profiles WHERE id = auth.uid())
        )
    );

-- Watchlist: users can manage their own watchlist
CREATE POLICY "Users can manage own watchlist"
    ON watchlist FOR ALL
    USING (user_id = auth.uid());

-- Watchlist: users can view family members' watchlists
CREATE POLICY "Users can view family watchlists"
    ON watchlist FOR SELECT
    USING (
        user_id IN (
            SELECT id FROM profiles
            WHERE family_id = (SELECT family_id FROM profiles WHERE id = auth.uid())
        )
    );

-- Function: automatically create profile on signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id, display_name, avatar_url)
    VALUES (
        NEW.id,
        COALESCE(NEW.raw_user_meta_data->>'full_name', NEW.email),
        COALESCE(NEW.raw_user_meta_data->>'avatar_url', '')
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger: run on new user signup
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- Index for performance
CREATE INDEX IF NOT EXISTS idx_holdings_user_id ON holdings(user_id);
CREATE INDEX IF NOT EXISTS idx_watchlist_user_id ON watchlist(user_id);
CREATE INDEX IF NOT EXISTS idx_profiles_family_id ON profiles(family_id);
