import { DemoDashboard } from "@/components/demo-dashboard";
import { getMatches, getPrediction } from "@/lib/api";

export default async function HomePage() {
  const matches = await getMatches();
  const prediction = await getPrediction(matches[0].id);

  return <DemoDashboard prediction={prediction} />;
}

