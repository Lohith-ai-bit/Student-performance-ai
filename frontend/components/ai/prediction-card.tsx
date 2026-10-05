"use client";

import { BrainCircuit, Info } from "lucide-react";

import { RiskBadge } from "@/components/risk-badge";
import { FactorList } from "@/components/ai/factor-list";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { ExplanationPayload } from "@/types/advanced";

export function PredictionCard({
  predictedScore,
  riskLevel,
  riskProbability,
  modelName,
  modelVersion,
  modelType,
  predictionDate,
  explanation,
  disclaimer,
}: {
  predictedScore: number;
  riskLevel: string;
  riskProbability?: number;
  modelName?: string;
  modelVersion?: string;
  modelType?: string;
  predictionDate?: string;
  explanation?: ExplanationPayload | null;
  disclaimer?: string;
}) {
  return (
    <Card className="animate-fade-up">
      <CardHeader className="items-center text-center">
        <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-accent text-accent-foreground">
          <BrainCircuit className="h-6 w-6" />
        </span>
        <CardTitle className="mt-2">AI Prediction</CardTitle>
        <CardDescription>
          {modelType ? `${modelType} · ` : ""}
          {modelName}
          {modelVersion ? ` v${modelVersion}` : ""}
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col items-center gap-4 text-center">
        <p className="text-5xl font-bold tracking-tight text-primary">{predictedScore.toFixed(1)}%</p>
        <RiskBadge level={riskLevel} />
        {riskProbability !== undefined && (
          <p className="text-xs text-muted-foreground">Risk probability: {(riskProbability * 100).toFixed(1)}%</p>
        )}
        {predictionDate && <p className="text-xs text-muted-foreground">{new Date(predictionDate).toLocaleString()}</p>}

        {explanation && (
          <div className="mt-2 w-full rounded-lg border bg-muted/30 p-4 text-left">
            <p className="mb-2 text-sm font-medium">Why this prediction?</p>
            {explanation.summary ? <p className="mb-3 text-sm text-muted-foreground">{explanation.summary}</p> : null}
            <FactorList factors={explanation.factors} />
            <p className="mt-3 text-xs text-muted-foreground">{explanation.disclaimer}</p>
          </div>
        )}
        {!explanation && disclaimer && (
          <div className="flex w-full items-start gap-2 rounded-lg border bg-muted/40 p-3 text-left">
            <Info className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
            <p className="text-xs text-muted-foreground">{disclaimer}</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
