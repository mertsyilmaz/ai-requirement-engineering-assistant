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
        confirmed_ambiguities = "\n".join(
            f"- {item.matched_text}: {item.reason} Evidence: {item.evidence}"
            for item in pre_analysis.confirmed_ambiguities
        ) or "- None"

        rejected_ambiguities = "\n".join(
            f"- {item.matched_text}: Do not report as ambiguity. "
            f"Reason: {item.rejection_reason} "
            f"Supporting expression: {item.supporting_expression}"
            for item in pre_analysis.rejected_ambiguity_candidates
        ) or "- None"

        reference_ambiguities = "\n".join(
            f"- {item.phrase}: {item.reason} Evidence: {item.evidence}"
            for item in pre_analysis.reference_ambiguities
        ) or "- None"

        measurement_ambiguities = "\n".join(
            f"- {item.phrase}: Missing {item.missing_dimension}. "
            f"Reason: {item.reason} Evidence: {item.evidence}"
            for item in pre_analysis.measurement_ambiguities
        ) or "- None"

        measurable_expressions = "\n".join(
            f"- {item.text}: {item.reason}"
            for item in pre_analysis.measurable_expressions
        ) or "- None"

        prompt_guidance = "\n".join(
            f"- {item}"
            for item in pre_analysis.prompt_guidance
        ) or "- None"

        return f"""
The system performed NLP-based pre-analysis before this prompt.

Confirmed ambiguities:
{confirmed_ambiguities}

Rejected ambiguity candidates:
{rejected_ambiguities}

Reference ambiguity findings:
{reference_ambiguities}

Measurement ambiguity findings:
{measurement_ambiguities}

Measurable expressions:
{measurable_expressions}

Prompt guidance:
{prompt_guidance}
""".strip()

    #---------- <Summary> ----------
    # Summary: Explains how the LLM should use V2 pre-analysis findings.
    #---------- </Summary> ----------
    def _v2_instruction_section(self) -> str:
        return """
Instructions:
- Use confirmed ambiguities as validated pre-analysis findings.
- Do not report rejected ambiguity candidates as ambiguities.
- Consider reference ambiguity findings when they are relevant.
- Use measurement ambiguity findings to clarify measurable targets that still lack scope, load, statistical target, or measurement boundaries.
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
