import { ArrowRight, BrainCircuit, ChartLine, ShieldCheck, Sparkles, Target } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardTitle } from "@/components/ui/card";

const FEATURES = [
  {
    icon: BrainCircuit,
    title: "Baseline ML Models",
    description: "Linear Regression, Random Forest, XGBoost and LightGBM trained on academic, attendance and behavioural features.",
  },
  {
    icon: Target,
    title: "Early Risk Detection",
    description: "A configurable risk classification (LOW / MEDIUM / HIGH / CRITICAL) flags students who need attention while there is still time to act.",
  },
  {
    icon: ChartLine,
    title: "Actionable Dashboards",
    description: "Students, faculty and admins each get tailored views of performance, attendance, engagement and predictions.",
  },
  {
    icon: ShieldCheck,
    title: "Role-Based Access",
    description: "Strict RBAC ensures students see only their own data, faculty see their assigned courses, and admins manage the institution.",
  },
];

export default function LandingPage() {
  return (
    <div className="hero-gradient min-h-screen">
      <header className="mx-auto flex w-full max-w-6xl items-center justify-between px-4 py-5">
        <div className="flex items-center gap-2 font-semibold">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <Sparkles className="h-4 w-4" />
          </span>
          EduPredict
        </div>
        <div className="flex items-center gap-2">
          <Button variant="ghost" asChild>
            <Link href="/login">Login</Link>
          </Button>
          <Button asChild>
            <Link href="/register">
              Get Started <ArrowRight />
            </Link>
          </Button>
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl px-4 pb-20">
        {/* Hero */}
        <section className="animate-fade-up flex flex-col items-center gap-6 py-20 text-center">
          <span className="rounded-full border bg-card/70 px-4 py-1 text-xs font-medium text-accent-foreground shadow-sm backdrop-blur">
            Hybrid Machine Learning · Transformer-ready architecture
          </span>
          <h1 className="max-w-3xl text-balance text-4xl font-bold tracking-tight md:text-6xl">
            AI-Powered Student Performance Prediction
          </h1>
          <p className="max-w-2xl text-balance text-lg text-muted-foreground">
            Predict academic performance early. Identify learning risks. Enable data-driven intervention.
          </p>
          <div className="flex flex-wrap items-center justify-center gap-3">
            <Button size="lg" asChild>
              <Link href="/register">
                Get Started <ArrowRight />
              </Link>
            </Button>
            <Button size="lg" variant="outline" asChild>
              <Link href="/login">Login</Link>
            </Button>
          </div>
        </section>

        {/* Features */}
        <section className="grid gap-4 md:grid-cols-2">
          {FEATURES.map((feature) => (
            <Card key={feature.title} className="animate-fade-up">
              <CardContent className="flex gap-4 p-6">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-accent text-accent-foreground">
                  <feature.icon className="h-5 w-5" />
                </span>
                <div>
                  <CardTitle>{feature.title}</CardTitle>
                  <CardDescription className="mt-1.5">{feature.description}</CardDescription>
                </div>
              </CardContent>
            </Card>
          ))}
        </section>

        <footer className="mt-16 text-center text-xs text-muted-foreground">
          EduPredict · Capstone Project · Predictions are AI-generated estimates intended to support learning and
          academic intervention — not definitive judgments of student ability.
        </footer>
      </main>
    </div>
  );
}
