class OKFNavigator:
    """
    Dynamic OKF navigator using the persisted
    BM25Okapi routing index.

    The actual OKF concepts and BM25 index are
    created offline by Notebook 1.
    """

    def __init__(
        self,
        concepts,
        bm25_index,
    ):

        self.concepts = concepts
        self.bm25_index = bm25_index

        self.hierarchy = {}

        for concept in self.concepts:

            domain = (
                concept["meta"]
                .get("domain", "unknown")
                .lower()
            )

            topic = (
                concept["meta"]
                .get("topic", "unknown")
                .lower()
            )

            if domain not in self.hierarchy:
                self.hierarchy[domain] = {}

            if topic not in self.hierarchy[domain]:
                self.hierarchy[domain][topic] = []

            self.hierarchy[domain][topic].append(
                concept
            )

    def _tokenize(
        self,
        text: str,
    ) -> list[str]:

        tokens = text.lower().split()

        return [
            token.strip(
                ".,;:!?'\"()[]{}"
            )
            for token in tokens
            if len(
                token.strip(
                    ".,;:!?'\"()[]{}"
                )
            ) > 1
        ]

    def route_query(
        self,
        query: str,
    ) -> dict:

        query_tokens = self._tokenize(
            query
        )

        scores = self.bm25_index.get_scores(
            query_tokens
        )

        scored = [
            (
                self.concepts[i],
                scores[i],
            )
            for i in range(
                len(self.concepts)
            )
        ]

        scored.sort(
            key=lambda x: x[1],
            reverse=True,
        )

        scored = [
            (concept, score)
            for concept, score in scored
            if score > 0
        ]

        # ----------------------------------------------------
        # Fallback
        # ----------------------------------------------------

        if not scored:

            all_sources = [
                concept["meta"]["source_file"]
                for concept in self.concepts
            ]

            return {
                "candidate_docs": all_sources,
                "provenance": [
                    {
                        "step": "fallback",
                        "reason": (
                            "no OKF concept matched"
                        ),
                    }
                ],
                "path": "no match → search all",
                "concept_scores": {},
            }

        # ----------------------------------------------------
        # Select concepts >= 50% of best score
        # ----------------------------------------------------

        best_score = scored[0][1]

        threshold = best_score * 0.50

        top_concepts = [
            (concept, score)
            for concept, score in scored
            if score >= threshold
        ]

        provenance = []

        candidate_docs = []

        concept_scores = {}

        for concept, score in top_concepts:

            meta = concept["meta"]

            source_file = meta.get(
                "source_file",
                "",
            )

            domain = meta.get(
                "domain",
                "?",
            )

            topic = meta.get(
                "topic",
                "?",
            )

            subtopic = meta.get(
                "subtopic",
                "",
            )

            nav_path = (
                f"{domain} → {topic}"
            )

            if (
                subtopic
                and subtopic.lower()
                != topic.lower()
            ):

                nav_path += (
                    f" → {subtopic}"
                )

            nav_path += (
                f" → {concept['rel_path']}"
            )

            query_lower = query.lower()

            tags_matched = [
                str(tag)
                for tag in meta.get(
                    "tags",
                    [],
                )
                if str(tag).lower()
                in query_lower
            ]

            provenance.append(
                {
                    "concept_file":
                        concept["rel_path"],
                    "title":
                        meta.get(
                            "title",
                            "",
                        ),
                    "domain":
                        domain,
                    "topic":
                        topic,
                    "subtopic":
                        subtopic,
                    "source_file":
                        source_file,
                    "score":
                        round(score, 4),
                    "nav_path":
                        nav_path,
                    "tags_matched":
                        tags_matched,
                }
            )

            if (
                source_file
                and source_file
                not in candidate_docs
            ):

                candidate_docs.append(
                    source_file
                )

            concept_scores[
                concept["rel_path"]
            ] = round(
                score,
                4,
            )

        path = (
            provenance[0]["nav_path"]
            if provenance
            else "unknown"
        )

        return {
            "candidate_docs":
                candidate_docs,

            "provenance":
                provenance,

            "path":
                path,

            "concept_scores":
                concept_scores,
        }