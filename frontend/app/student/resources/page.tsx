"use client";

import { useQuery } from "@tanstack/react-query";
import { BookOpen, ExternalLink, Search } from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { apiGet } from "@/lib/api";
import type { LearningResource } from "@/types/advanced";

const RESOURCE_TYPES = ["VIDEO", "ARTICLE", "DOCUMENT", "QUIZ", "PRACTICE", "ASSIGNMENT"];
const DIFFICULTIES = ["BEGINNER", "INTERMEDIATE", "ADVANCED"];

export default function StudentResourcesPage() {
  const [search, setSearch] = useState("");
  const [resourceType, setResourceType] = useState("");
  const [difficulty, setDifficulty] = useState("");

  const resources = useQuery({
    queryKey: ["resources", search, resourceType, difficulty],
    queryFn: () =>
      apiGet<LearningResource[]>("/resources", {
        search: search || undefined,
        resource_type: resourceType || undefined,
        difficulty: difficulty || undefined,
        limit: 60,
      }),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Learning Resources</h1>
        <p className="mt-1 text-sm text-muted-foreground">Browse study material by topic, type and difficulty</p>
      </div>

      <Card>
        <CardContent className="flex flex-wrap items-center gap-3 p-4">
          <div className="relative min-w-52 flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              className="pl-9"
              placeholder="Search resources…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <Select value={resourceType} onValueChange={(v) => setResourceType(v === "all" ? "" : v)}>
            <SelectTrigger className="w-44">
              <SelectValue placeholder="Any type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Any type</SelectItem>
              {RESOURCE_TYPES.map((t) => (
                <SelectItem key={t} value={t}>
                  {t}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={difficulty} onValueChange={(v) => setDifficulty(v === "all" ? "" : v)}>
            <SelectTrigger className="w-44">
              <SelectValue placeholder="Any difficulty" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Any difficulty</SelectItem>
              {DIFFICULTIES.map((d) => (
                <SelectItem key={d} value={d}>
                  {d}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </CardContent>
      </Card>

      {resources.isLoading ? (
        <div className="grid gap-3 md:grid-cols-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
      ) : (resources.data ?? []).length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="p-10 text-center text-sm text-muted-foreground">
            No resources match the current filters.
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-3 md:grid-cols-2">
          {(resources.data ?? []).map((r) => (
            <Card key={r.id} className="transition-shadow hover:shadow-md">
              <CardContent className="flex h-full flex-col gap-2 p-4">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <BookOpen className="h-4 w-4 text-primary" />
                    <p className="font-medium leading-tight">{r.title}</p>
                  </div>
                  <Badge variant="outline">{r.difficulty}</Badge>
                </div>
                <p className="line-clamp-2 text-sm text-muted-foreground">{r.description}</p>
                <div className="mt-auto flex items-center justify-between pt-2">
                  <div className="flex gap-1.5">
                    <Badge variant="secondary">{r.resource_type}</Badge>
                    <Badge variant="secondary">{r.estimated_minutes} min</Badge>
                  </div>
                  <Button size="sm" variant="outline" asChild>
                    <a href={r.url} target="_blank" rel="noreferrer">
                      Open <ExternalLink />
                    </a>
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
