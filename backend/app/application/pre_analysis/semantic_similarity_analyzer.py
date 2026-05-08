import logging

import torch
import torch.nn.functional as functional
from transformers import AutoModel, AutoTokenizer

from app.application.ports.ambiguity_knowledge_repository import (
    AmbiguityKnowledgeRepositoryPort,
)
from app.domain.pre_analysis import (
    AmbiguityTerm,
    ConfirmedAmbiguity,
    RejectedAmbiguityCandidate,
    SemanticAmbiguityFinding,
)

logger = logging.getLogger(__name__)


#---------- <Summary> ----------
# Summary: Connects NLP-derived ambiguity candidates with known ambiguity knowledge by meaning.
#
# This analyzer replaces the previous zero-shot label classifier. It does not
# ask a model to choose from fixed labels. Instead, it embeds candidate phrases
# and known ambiguity descriptions, then checks whether a candidate is
# semantically close to existing requirement ambiguity knowledge.
#---------- </Summary> ----------
class SemanticSimilarityAnalyzer:

    def __init__(
        self,
        ambiguity_repository: AmbiguityKnowledgeRepositoryPort,
        model_name: str = "sentence-transformers/all-mpnet-base-v2",
        similarity_threshold: float = 0.50,
    ):
        self.ambiguity_repository = ambiguity_repository
        self.model_name = model_name
        self.similarity_threshold = similarity_threshold
        self.tokenizer = None
        self.model = None
        self._knowledge_terms: list[AmbiguityTerm] | None = None
        self._model_available: bool | None = None

    #---------- <Summary> ----------
    # Summary: Adds semantic findings to confirmed candidates without relying on fixed labels.
    #---------- </Summary> ----------
    def analyze(
        self,
        confirmed_ambiguities: list[ConfirmedAmbiguity],
        rejected_candidates: list[RejectedAmbiguityCandidate],
    ) -> tuple[
        list[ConfirmedAmbiguity],
        list[RejectedAmbiguityCandidate],
        list[SemanticAmbiguityFinding],
    ]:
        if not confirmed_ambiguities:
            return confirmed_ambiguities, rejected_candidates, []

        findings: list[SemanticAmbiguityFinding] = []
        enriched_confirmed: list[ConfirmedAmbiguity] = []

        for ambiguity in confirmed_ambiguities:
            exact_finding = self._find_exact_known_meaning(ambiguity)
            if exact_finding:
                findings.append(exact_finding)
                enriched_confirmed.append(
                    self._attach_semantic_guidance(ambiguity, exact_finding)
                )
                continue

            if not self._ensure_model_loaded():
                enriched_confirmed.append(ambiguity)
                continue

            finding = self._find_closest_known_meaning(ambiguity)

            if not finding:
                enriched_confirmed.append(ambiguity)
                continue

            findings.append(finding)
            enriched_confirmed.append(
                self._attach_semantic_guidance(ambiguity, finding)
            )

        return enriched_confirmed, rejected_candidates, findings

    #---------- <Summary> ----------
    # Summary: Returns semantic support immediately when a candidate exactly matches seed knowledge.
    #---------- </Summary> ----------
    def _find_exact_known_meaning(
        self,
        ambiguity: ConfirmedAmbiguity,
    ) -> SemanticAmbiguityFinding | None:
        for term in self._select_knowledge_terms(ambiguity):
            if term.phrase.lower() != ambiguity.matched_text.lower():
                continue

            return SemanticAmbiguityFinding(
                phrase=ambiguity.matched_text,
                decision="confirmed",
                semantic_label=(
                    f"similar to known {term.category} ambiguity "
                    f"'{term.phrase}'"
                ),
                interpretation=(
                    f"The candidate directly matches known ambiguity "
                    f"'{term.phrase}'."
                ),
                prompt_guidance=(
                    "Use this as semantic support, not as an absolute decision."
                ),
                category=term.category,
                start_char=ambiguity.start_char,
                end_char=ambiguity.end_char,
                sentence=ambiguity.sentence,
            )

        return None

    #---------- <Summary> ----------
    # Summary: Loads the embedding model only when semantic similarity is needed.
    #---------- </Summary> ----------
    def _ensure_model_loaded(self) -> bool:
        if self._model_available is not None:
            return self._model_available

        try:
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                local_files_only=True,
            )
            self.model = AutoModel.from_pretrained(
                self.model_name,
                local_files_only=True,
            )
            self.model.eval()
            self._model_available = True
        except Exception as error:
            logger.warning(
                "Semantic similarity model is not available locally. "
                "V2 will continue without semantic similarity findings. Error: %s",
                str(error),
            )
            self._model_available = False

        return self._model_available

    #---------- <Summary> ----------
    # Summary: Finds the known ambiguity term that is closest in meaning to a candidate.
    #---------- </Summary> ----------
    def _find_closest_known_meaning(
        self,
        ambiguity: ConfirmedAmbiguity,
    ) -> SemanticAmbiguityFinding | None:
        knowledge_terms = self._select_knowledge_terms(ambiguity)
        if not knowledge_terms:
            return None

        candidate_embedding = self._encode_text(self._build_candidate_text(ambiguity))
        knowledge_embeddings = self._encode_texts(
            [
                self._build_knowledge_text(term)
                for term in knowledge_terms
            ]
        )

        similarities = functional.cosine_similarity(
            candidate_embedding.expand_as(knowledge_embeddings),
            knowledge_embeddings,
            dim=1,
        )
        best_index = int(torch.argmax(similarities).item())
        best_score = float(similarities[best_index].item())

        if best_score < self.similarity_threshold:
            return None

        closest_term = knowledge_terms[best_index]

        return SemanticAmbiguityFinding(
            phrase=ambiguity.matched_text,
            decision="confirmed",
            semantic_label=(
                f"similar to known {closest_term.category} ambiguity "
                f"'{closest_term.phrase}'"
            ),
            interpretation=(
                f"The candidate is semantically close to known ambiguity "
                f"'{closest_term.phrase}' with similarity score {best_score:.2f}."
            ),
            prompt_guidance=(
                "Use this as semantic support, not as an absolute decision."
            ),
            category=closest_term.category,
            start_char=ambiguity.start_char,
            end_char=ambiguity.end_char,
            sentence=ambiguity.sentence,
        )

    #---------- <Summary> ----------
    # Summary: Returns ambiguity terms that act as semantic seed knowledge.
    #---------- </Summary> ----------
    def _get_knowledge_terms(self) -> list[AmbiguityTerm]:
        if self._knowledge_terms is None:
            self._knowledge_terms = self.ambiguity_repository.get_all_terms()

        return self._knowledge_terms

    #---------- <Summary> ----------
    # Summary: Chooses the most useful seed terms before semantic comparison.
    #---------- </Summary> ----------
    def _select_knowledge_terms(
        self,
        ambiguity: ConfirmedAmbiguity,
    ) -> list[AmbiguityTerm]:
        terms = self._get_knowledge_terms()

        same_category_terms = [
            term
            for term in terms
            if term.category == ambiguity.category
        ]
        if same_category_terms:
            return same_category_terms

        if ambiguity.category == "quality":
            specific_quality_terms = [
                term
                for term in terms
                if term.category != "quality"
            ]
            if specific_quality_terms:
                return specific_quality_terms

        return terms

    #---------- <Summary> ----------
    # Summary: Builds semantic text for a candidate phrase in its sentence context.
    #---------- </Summary> ----------
    def _build_candidate_text(self, ambiguity: ConfirmedAmbiguity) -> str:
        return (
            f"Requirement sentence: {ambiguity.sentence}\n"
            f"Candidate phrase: {ambiguity.matched_text}\n"
            f"Candidate role: {ambiguity.linguistic_role or ambiguity.reason}"
        )

    #---------- <Summary> ----------
    # Summary: Builds semantic text for one known ambiguity seed item.
    #---------- </Summary> ----------
    def _build_knowledge_text(self, term: AmbiguityTerm) -> str:
        return (
            f"Known ambiguous requirement phrase: {term.phrase}\n"
            f"Category: {term.category}"
        )

    #---------- <Summary> ----------
    # Summary: Encodes one text into a normalized embedding vector.
    #---------- </Summary> ----------
    def _encode_text(self, text: str):
        return self._encode_texts([text])

    #---------- <Summary> ----------
    # Summary: Encodes multiple texts using mean pooling over transformer token embeddings.
    #---------- </Summary> ----------
    def _encode_texts(self, texts: list[str]):
        encoded = self.tokenizer(
            texts,
            padding=True,
            truncation=True,
            return_tensors="pt",
        )

        with torch.no_grad():
            model_output = self.model(**encoded)

        token_embeddings = model_output.last_hidden_state
        attention_mask = encoded["attention_mask"].unsqueeze(-1)
        masked_embeddings = token_embeddings * attention_mask
        summed_embeddings = masked_embeddings.sum(dim=1)
        token_counts = attention_mask.sum(dim=1).clamp(min=1)
        embeddings = summed_embeddings / token_counts

        return functional.normalize(embeddings, p=2, dim=1)

    #---------- <Summary> ----------
    # Summary: Adds semantic support text to a confirmed ambiguity finding.
    #---------- </Summary> ----------
    def _attach_semantic_guidance(
        self,
        ambiguity: ConfirmedAmbiguity,
        finding: SemanticAmbiguityFinding,
    ) -> ConfirmedAmbiguity:
        return ConfirmedAmbiguity(
            phrase=ambiguity.phrase,
            matched_text=ambiguity.matched_text,
            reason=ambiguity.reason,
            severity=ambiguity.severity,
            category=ambiguity.category,
            start_char=ambiguity.start_char,
            end_char=ambiguity.end_char,
            sentence=ambiguity.sentence,
            evidence=(
                f"{ambiguity.evidence} Semantic support: "
                f"{finding.interpretation}"
            ),
            source=ambiguity.source,
            linguistic_role=ambiguity.linguistic_role,
            prompt_guidance=finding.prompt_guidance,
        )
