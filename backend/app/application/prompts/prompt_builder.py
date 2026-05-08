from app.domain.pre_analysis import PreAnalysisResult


#---------- <Summary> ----------
# Summary: Builds LLM prompts from the selected analysis version context.
#
# The output JSON contract stays shared across versions. Version-specific
# methods only change which context is added before the common output rules.
#---------- </Summary> ----------
class PromptBuilder:
    #---------- <Summary> ----------
    # Summary: Builds the direct LLM prompt for V1.
    #---------- </Summary> ----------
    def build_v1_prompt(self, text: str) -> str:
        return "\n\n".join(
            [
                self._role_section(),
                self._v1_requirement_input_section(text),
                self._output_contract_section(),
                self._output_rules_section(),
            ]
        )

    #---------- <Summary> ----------
    # Summary: Builds the V2 prompt enriched with NLP pre-analysis findings.
    #---------- </Summary> ----------
    def build_v2_prompt(self, pre_analysis: PreAnalysisResult) -> str:
        if not self._has_meaningful_pre_analysis(pre_analysis):
            return self.build_v1_prompt(pre_analysis.cleaned_text)

        return "\n\n".join(
            [
                self._role_section(),
                self._v2_requirement_input_section(pre_analysis),
                self._v2_pre_analysis_section(pre_analysis),
                self._v2_instruction_section(),
                self._output_contract_section(),
                self._output_rules_section(),
            ]
        )

    #---------- <Summary> ----------
    # Summary: Checks whether V2 has useful findings to add to the prompt.
    #---------- </Summary> ----------
    def _has_meaningful_pre_analysis(self, pre_analysis: PreAnalysisResult) -> bool:
        return any(
            [
                pre_analysis.confirmed_ambiguities,
                pre_analysis.rejected_ambiguity_candidates,
                pre_analysis.reference_ambiguities,
                pre_analysis.measurement_ambiguities,
                pre_analysis.measurement_contexts,
                [
                    item
                    for item in pre_analysis.semantic_findings
                    if item.decision != "uncertain"
                ],
            ]
        )

    #---------- <Summary> ----------
    # Summary: Defines the role the LLM should follow.
    #---------- </Summary> ----------
    def _role_section(self) -> str:
        return """
You are a software requirements engineering assistant.
""".strip()

    #---------- <Summary> ----------
    # Summary: Adds the requirement text for direct analysis.
    #---------- </Summary> ----------
    def _v1_requirement_input_section(self, text: str) -> str:
        return f"""
Analyze the following requirement:
{text}
""".strip()

    #---------- <Summary> ----------
    # Summary: Adds the cleaned requirement text produced by pre-analysis.
    #---------- </Summary> ----------
    def _v2_requirement_input_section(self, pre_analysis: PreAnalysisResult) -> str:
        return f"""
Analyze the following cleaned requirement:
{pre_analysis.cleaned_text}
""".strip()

    #---------- <Summary> ----------
    # Summary: Formats V2 pre-analysis findings as structured prompt context.
    #---------- </Summary> ----------
    def _v2_pre_analysis_section(self, pre_analysis: PreAnalysisResult) -> str:
        sections: list[str] = ["Pre-analysis:"]
        finding_sections: list[str] = []
        context_sections: list[str] = []

        confirmed = [
            f"- {item.matched_text} [{item.category}]: {item.reason}"
            for item in pre_analysis.confirmed_ambiguities
        ]
        if confirmed:
            finding_sections.append("Confirmed ambiguity findings:\n" + "\n".join(confirmed))

        semantic = [
            f"- {item.phrase} [{item.semantic_label}]: {item.interpretation}"
            for item in pre_analysis.semantic_findings
            if item.decision == "confirmed"
        ]
        if semantic:
            context_sections.append("Semantic observations:\n" + "\n".join(semantic))

        measurement = [
            f"- {item.phrase}: missing {item.missing_dimension}"
            for item in pre_analysis.measurement_ambiguities
        ]
        if measurement:
            finding_sections.append("Measurement gaps:\n" + "\n".join(measurement))

        reference = [
            f"- {item.phrase} [{item.category}]: unclear reference"
            for item in pre_analysis.reference_ambiguities
        ]
        if reference:
            finding_sections.append("Reference findings:\n" + "\n".join(reference))

        excluded = [
            f"- {item.matched_text}: {item.prompt_guidance or item.rejection_reason}"
            for item in pre_analysis.rejected_ambiguity_candidates
        ]
        excluded.extend(
            f"- {item.phrase}: {item.prompt_guidance}"
            for item in pre_analysis.semantic_findings
            if item.decision == "excluded"
        )
        excluded = list(dict.fromkeys(excluded))
        if excluded:
            finding_sections.append("Rejected or excluded findings:\n" + "\n".join(excluded))

        measurement_context = self._format_measurement_contexts(pre_analysis)
        if measurement_context:
            context_sections.append("Measurement context observations:\n" + measurement_context)

        if finding_sections:
            sections.append(
                "Pre-analysis findings:\n" + "\n\n".join(finding_sections)
            )

        if context_sections:
            sections.append(
                "Context observations:\n" + "\n\n".join(context_sections)
            )

        return "\n\n".join(sections)

    #---------- <Summary> ----------
    # Summary: Formats structural measurement context as non-mandatory prompt support.
    #---------- </Summary> ----------
    def _format_measurement_contexts(self, pre_analysis: PreAnalysisResult) -> str:
        context_lines: list[str] = []

        for item in pre_analysis.measurement_contexts:
            details: list[str] = []

            if item.percentage_target and item.percentage_subject:
                details.append(
                    f"{item.percentage_target} is attached to \"{item.percentage_subject}\""
                )

            if item.load_context:
                details.append(f"load context appears to be \"{item.load_context}\"")

            if item.statistical_target:
                details.append(f"statistical target appears to be \"{item.statistical_target}\"")

            if item.measured_item:
                details.append(f"measured item appears to be \"{item.measured_item}\"")

            if item.nearby_action:
                details.append(
                    f"related action appears to be \"{item.nearby_action}\""
                )

            if item.time_target:
                details.append(f"time target is \"{item.time_target}\"")

            if item.condition:
                details.append(f"condition phrase is \"{item.condition}\"")

            if details:
                context_lines.append("- " + "; ".join(details))

        return "\n".join(context_lines)

    #---------- <Summary> ----------
    # Summary: Explains how the LLM should use V2 pre-analysis findings.
    #---------- </Summary> ----------
    def _v2_instruction_section(self) -> str:
        return """
Instructions:
- Use the pre-analysis as supporting context.
- Do not report excluded findings as ambiguities.
- Use context observations as supporting context only; do not force them as ambiguities unless the requirement text supports it.
- You may add other ambiguities only if they are clearly supported by the requirement text.
- Preserve the meaning of the original requirement.
- Generate a clearer and more testable improved requirement.
- Generate multiple improved requirement alternatives with different clarification levels.
""".strip()

    #---------- <Summary> ----------
    # Summary: Defines the JSON fields expected from every analysis version.
    #---------- </Summary> ----------
    def _output_contract_section(self) -> str:
        return """
Return a JSON object with these fields:
- userStory
- requirementType
- ambiguities
- suggestions
- improvedText
- improvedTextOptions
""".strip()

    #---------- <Summary> ----------
    # Summary: Defines strict formatting and validation rules for the LLM response.
    #---------- </Summary> ----------
    def _output_rules_section(self) -> str:
        return """
Rules:
- The userStory MUST strictly follow this format:
  "As a <type of user>, I want <goal>, so that <reason>."
- Do not use any other user story format.
- requirementType must be one of: Functional, Performance, Security, Usability, Reliability, Maintainability, Portability, Other
- ambiguities must be an array of objects with: phrase, reason, severity
- suggestions must be an array of objects with: originalPart, suggestedPart, reason
- improvedText must contain the best single improved requirement.
- improvedTextOptions must be an array of objects with: label, text, reason
- improvedTextOptions should include three alternatives: Minimal, Balanced, Strict
- Return only valid JSON
""".strip()
