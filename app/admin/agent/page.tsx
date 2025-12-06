"use client";

import { useEffect, useState } from "react";
import { createClient } from "@supabase/supabase-js";

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

export default function AgentSettingsPage() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [agentPrompt, setAgentPrompt] = useState("");
  const [actionTemplates, setActionTemplates] = useState("");

  async function loadSettings() {
    setLoading(true);
    const { data, error } = await supabase.from("settings").select("*").limit(1).single();
    setLoading(false);

    if (error) {
      alert("Failed to load settings");
      return;
    }

    if (data) {
      setAgentPrompt(data.agent_prompt || "");
      setActionTemplates(JSON.stringify(data.action_templates || [], null, 2));
    }
  }

  async function saveSettings() {
    setSaving(true);

    let parsedActions = [];
    try {
      parsedActions = JSON.parse(actionTemplates);
    } catch (e) {
      alert("Action templates must be valid JSON");
      setSaving(false);
      return;
    }

    const { error } = await supabase
      .from("settings")
      .update({
        agent_prompt: agentPrompt,
        action_templates: parsedActions,
        updated_at: new Date().toISOString()
      })
      .neq("id", ""); // update the single row

    setSaving(false);

    if (error) {
      alert("Failed to save");
    } else {
      alert("Saved!");
    }
  }

  async function resetDefaults() {
    const defaultPrompt = `You are Jurio, a Mongolian legal assistant that helps users understand laws and court cases. 
You must follow Mongolian legal terminology and explain simply.`;

    const defaultActions = [
      { id: "find_lawyer", label: "Find a Lawyer", type: "navigate", target: "/lawyers" },
      { id: "next_steps", label: "What’s Next?", type: "followup" },
      { id: "generate_contract", label: "Generate Contract", type: "tool", tool: "generate_contract" }
    ];

    setAgentPrompt(defaultPrompt);
    setActionTemplates(JSON.stringify(defaultActions, null, 2));
  }

  useEffect(() => {
    loadSettings();
  }, []);

  return (
    <div style={{ padding: "30px", maxWidth: "900px", margin: "0 auto" }}>
      <h1 style={{ fontSize: "28px", marginBottom: "20px" }}>🧠 Jurio Agent Settings</h1>

      {loading ? (
        <p>Loading...</p>
      ) : (
        <>
          <label style={{ fontWeight: "bold" }}>Agent Personality Prompt</label>
          <textarea
            value={agentPrompt}
            onChange={(e) => setAgentPrompt(e.target.value)}
            style={{
              width: "100%",
              height: "180px",
              margin: "10px 0",
              padding: "10px",
              fontSize: "14px"
            }}
          />

          <label style={{ fontWeight: "bold" }}>Action Templates (JSON)</label>
          <textarea
            value={actionTemplates}
            onChange={(e) => setActionTemplates(e.target.value)}
            style={{
              width: "100%",
              height: "200px",
              margin: "10px 0",
              padding: "10px",
              fontSize: "14px",
              fontFamily: "monospace"
            }}
          />

          <button
            onClick={saveSettings}
            disabled={saving}
            style={{
              padding: "10px 20px",
              background: "#2563eb",
              borderRadius: "6px",
              color: "white",
              marginRight: "10px"
            }}
          >
            {saving ? "Saving..." : "Save Settings"}
          </button>

          <button
            onClick={resetDefaults}
            style={{
              padding: "10px 20px",
              background: "#555",
              borderRadius: "6px",
              color: "white"
            }}
          >
            Reset to Default
          </button>
        </>
      )}
    </div>
  );
}