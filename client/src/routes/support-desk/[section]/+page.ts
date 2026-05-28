import { error } from "@sveltejs/kit";
import type { PageLoad } from "./$types";
import { getSupportDeskPageConfig } from "$lib/supportDesk";

export const load: PageLoad = ({ params }) => {
  const section = getSupportDeskPageConfig(params.section);

  if (!section || section.key === "overview") {
    throw error(404, "Support Desk section not found");
  }

  return { section };
};
