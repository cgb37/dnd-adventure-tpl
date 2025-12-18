## [0.1.1](https://github.com/cgb37/dnd-adventure-tpl/compare/v0.1.0...v0.1.1) (2025-12-18)


* Implements a new script for scaffolding issue resolution summary documents. ([ad0f32e](https://github.com/cgb37/dnd-adventure-tpl/commit/ad0f32efe47b1e09398bbb35e731f8026e8cbe3f))


### Bug Fixes

* **docker:** update CORS settings and LLM provider ([f716434](https://github.com/cgb37/dnd-adventure-tpl/commit/f716434a1cddbba8f8b2393fef07cc4c5b8d7003))
* **gallery:** address Jekyll error in gallery rendering ([82c77cd](https://github.com/cgb37/dnd-adventure-tpl/commit/82c77cd1e762891d618817a89a148286288046d2)), closes [#456](https://github.com/cgb37/dnd-adventure-tpl/issues/456)


### Code Refactoring

* **prompts:** rename iteration document to issue planning document ([93edec3](https://github.com/cgb37/dnd-adventure-tpl/commit/93edec340873e6cef7de6e09e1aa4aef69b50d1c))


### Features

* **chatbot:** enhance desktop split-view layout and testing ([f32b957](https://github.com/cgb37/dnd-adventure-tpl/commit/f32b95795c7e709f42916ff2efefadf99fcc9ebf))
* **chatbot:** enhance responsive layout support ([85322ff](https://github.com/cgb37/dnd-adventure-tpl/commit/85322ffa437da02196e47ced70a2dd24e61fdac7))
* **meta:** add mock provider for local development ([3d2bc36](https://github.com/cgb37/dnd-adventure-tpl/commit/3d2bc361a3efed45f9d501776263ca31f017578a))
* **pr-resolution-doc:** add PR resolution documentation generator ([7b962eb](https://github.com/cgb37/dnd-adventure-tpl/commit/7b962eba14d0dcf2a1819057ecab4d9360396e47))
* **prompt:** add design prompt for ui-chatbot layout ([7aa0935](https://github.com/cgb37/dnd-adventure-tpl/commit/7aa09356370c838f80ffe6f3f287ce3923f2bd8a))
* **prompts:** enhance iteration-doc template structure ([3d026fb](https://github.com/cgb37/dnd-adventure-tpl/commit/3d026fbc0c0e6affa1edb5fa2293f656807845f4))
* **scripts:** add docker-compose command for development ([6fe99c5](https://github.com/cgb37/dnd-adventure-tpl/commit/6fe99c5d782c41e65266a755aa1a36a44482cf8d)), closes [#5](https://github.com/cgb37/dnd-adventure-tpl/issues/5)
* **test:** add waitForLlmApiReady utility function ([b1461aa](https://github.com/cgb37/dnd-adventure-tpl/commit/b1461aaed0c0fdadfb7efcf90a72665d942ea1af))
* **vscode:** add task for running UI tests ([2634833](https://github.com/cgb37/dnd-adventure-tpl/commit/2634833c38819cdf3181e3358482ce381b806b02))


### BREAKING CHANGES

* **pr-resolution-doc:** The method for fetching PR data has been altered; ensure compatibility with existing workflows.
* Argument changes from iterationNumber and slug to issueTitleSlug, altering the input parameters significantly.
* **prompts:** The prompt's name and argument structure have changed, potentially affecting existing integrations.



# 0.1.0 (2025-12-17)


* <feat(security): add API key authentication for requests> ([f80db21](https://github.com/cgb37/dnd-adventure-tpl/commit/f80db212018deb7d97b285a338124fd68af554f2))


### Bug Fixes

* **factory:** replace ValueError with ApiError for config issues ([905d0f2](https://github.com/cgb37/dnd-adventure-tpl/commit/905d0f23f78b0f6d3af344e686c288601de5ec5b))
* search generator constantly reload ([06d4fb0](https://github.com/cgb37/dnd-adventure-tpl/commit/06d4fb053c7d3f48eb6d3811441295d7f2b4e48f))
* styles ([b8be372](https://github.com/cgb37/dnd-adventure-tpl/commit/b8be372b51232aceae6187cb23256191ff3b02c2))
* **webServer:** update directory for static files ([9c9f4ee](https://github.com/cgb37/dnd-adventure-tpl/commit/9c9f4eef979c06b18cd684f37bcd3548656f2af4))


### Features

* **active-campaign:** add functionality to manage active campaigns ([34a6618](https://github.com/cgb37/dnd-adventure-tpl/commit/34a6618806e7655abfc9acae90bb91e3548328ce))
* add chapter episode scene h2 ([5730ea0](https://github.com/cgb37/dnd-adventure-tpl/commit/5730ea01efe1f52bacc436da133520da6c68a308))
* add comprehensive .gitignore file ([f5723c7](https://github.com/cgb37/dnd-adventure-tpl/commit/f5723c7805e88c3299be23d714b0840d295f27fe))
* **api:** add AI content generator service ([9fd9c89](https://github.com/cgb37/dnd-adventure-tpl/commit/9fd9c8999a676145556a24241083ac0ea0d0a57a))
* **api:** add draft generation service using FastAPI ([9adc40a](https://github.com/cgb37/dnd-adventure-tpl/commit/9adc40a845b4639b54b6a3a165ab65345611f2c6)), closes [#1](https://github.com/cgb37/dnd-adventure-tpl/issues/1)
* **api:** add initial FastAPI application setup ([71a48f0](https://github.com/cgb37/dnd-adventure-tpl/commit/71a48f018e571e06c8d3c2d4f187ac68a1405a5a))
* **api:** add initial LLM API module ([466d4f0](https://github.com/cgb37/dnd-adventure-tpl/commit/466d4f00c2b8c5378b3220443345180e5c64d40d))
* **api:** add llm_api provider initialization module ([9cb04e8](https://github.com/cgb37/dnd-adventure-tpl/commit/9cb04e89659a8960cb499bddb320e6410bbf9d55))
* **campaign:** add subproject for rpg-theForsakenCrown ([81559ef](https://github.com/cgb37/dnd-adventure-tpl/commit/81559ef526fcc0c82ad043ab8cb7556860a936ba))
* chapter toc and remove episodes and scenes from chapters nav ([6f76183](https://github.com/cgb37/dnd-adventure-tpl/commit/6f76183ff3e12f57ab5a1827387e9577060de882))
* **chapter-generation:** handle missing chapters directory ([995b365](https://github.com/cgb37/dnd-adventure-tpl/commit/995b365d90298f6fe9f03c52eede63675ef55a20))
* **chapter-generator:** add chapter content generation functionality ([65e9040](https://github.com/cgb37/dnd-adventure-tpl/commit/65e9040d93ecf2aac057b122955609d6bd140615))
* **chapter:** add provider override for chapter generation ([1af3169](https://github.com/cgb37/dnd-adventure-tpl/commit/1af31697ff5ed2c28a0f6716fd23d5310af9b31d))
* chapters data with plugin ([782ff11](https://github.com/cgb37/dnd-adventure-tpl/commit/782ff110d5b74e72c48f7ece8c6d8809d4b5efb9))
* **chapters:** enhance front matter reading ([23660ae](https://github.com/cgb37/dnd-adventure-tpl/commit/23660ae0b7678604d3fe540addbb01997117e132))
* **chat:** add AI chatbot user interface ([858981e](https://github.com/cgb37/dnd-adventure-tpl/commit/858981e200fce141ea71a34b7d28f0b5fade2ffd))
* **chatbot:** add chatbot widget for user interaction ([41cb3f0](https://github.com/cgb37/dnd-adventure-tpl/commit/41cb3f0723742d360d2c37ba10f41a16492b84d4))
* **chatbot:** add global chatbot configuration ([c6c2f7d](https://github.com/cgb37/dnd-adventure-tpl/commit/c6c2f7d4ddf605281eca7891150239bf5dd043fb))
* **chatbot:** add global chatbot functionality to DM pages ([38a23c9](https://github.com/cgb37/dnd-adventure-tpl/commit/38a23c927a74f4f50753c39ecba97cee506186a3))
* **chatbot:** add global chatbot UI for DM content pages ([d4b27cf](https://github.com/cgb37/dnd-adventure-tpl/commit/d4b27cf1fa866daa2688b118927cd48b2dc343de))
* **chatbot:** add global chatbot widget with interaction features ([5c56ffc](https://github.com/cgb37/dnd-adventure-tpl/commit/5c56ffcb1c0fe10dd5139321979cde7d3f57c434))
* **chatbot:** add Jekyll UI chatbot for draft generation ([6eeff8e](https://github.com/cgb37/dnd-adventure-tpl/commit/6eeff8e04a4ba059c9060791502d79402261089b))
* **chatbot:** add LLM chatbot functionality ([ecec07a](https://github.com/cgb37/dnd-adventure-tpl/commit/ecec07a81a6b2dcd9e1854152ab9984fe1cf7871))
* **chatbot:** add responsive chatbot styling ([312d473](https://github.com/cgb37/dnd-adventure-tpl/commit/312d473406913e2c2d6f5d378ea498ecb47f6fbe))
* **chatbot:** implement global chatbot UI with split view ([42704ea](https://github.com/cgb37/dnd-adventure-tpl/commit/42704ea53d43bb0a83f9b1223a9b563eb6a769e1)), closes [#3](https://github.com/cgb37/dnd-adventure-tpl/issues/3)
* **chatbot:** integrate chatbot functionality into layout ([bba5692](https://github.com/cgb37/dnd-adventure-tpl/commit/bba5692bf6715dbd26bec266039557a5d33e9c48))
* **chatbot:** introduce global chatbot UI for DM pages ([ef0d68f](https://github.com/cgb37/dnd-adventure-tpl/commit/ef0d68fc022c25b76ed380f680519642315af434)), closes [#3](https://github.com/cgb37/dnd-adventure-tpl/issues/3)
* **config:** add LLM API configuration settings ([5594171](https://github.com/cgb37/dnd-adventure-tpl/commit/55941716f8af450137885b7f8d53811137d32aa3))
* **config:** add local API URL for chatbot development ([dca8824](https://github.com/cgb37/dnd-adventure-tpl/commit/dca8824a71abf4f09333e079f30efc0172425dc1))
* **config:** add localhost authentication and UI origin settings ([af45e9d](https://github.com/cgb37/dnd-adventure-tpl/commit/af45e9d720f7482d5cd0db14df3a9472fe9add9b))
* **constants:** add deterministic UUIDv5 namespace constant ([9c29a96](https://github.com/cgb37/dnd-adventure-tpl/commit/9c29a969494e79c3d23deff0552be1c6cbee97d6))
* **dispatch:** add content generation functionality ([f4cb578](https://github.com/cgb37/dnd-adventure-tpl/commit/f4cb5787adb5ac02ce6abf9993bbfabc34782c5d))
* **dispatch:** add provider override to generation methods ([010ea18](https://github.com/cgb37/dnd-adventure-tpl/commit/010ea181fc77038ddac1b7308fa5ae09ce791874))
* **docs:** add consolidated Core Python coding conventions ([55a4c91](https://github.com/cgb37/dnd-adventure-tpl/commit/55a4c915162734bee796fb569335cf9d56e50b93))
* **docs:** add Iteration 3 overview for Jekyll UI Chatbot ([bdbd8d7](https://github.com/cgb37/dnd-adventure-tpl/commit/bdbd8d7ff449c94c49f5aa51971bb5e2f73944c0))
* **docs:** add iteration documentation prompt ([81277a6](https://github.com/cgb37/dnd-adventure-tpl/commit/81277a6ce5029e16061d2817cf2dad430f521c35)), closes [#3-feat-add-chatbot-to-all-view-ports](https://github.com/cgb37/dnd-adventure-tpl/issues/3-feat-add-chatbot-to-all-view-ports)
* **drafts:** add draft writing functionality ([56ec940](https://github.com/cgb37/dnd-adventure-tpl/commit/56ec9409e03ab45b7d50a236c88a24f6be9c8a7f))
* **encounter:** add AI content generator for D&D encounters ([690125b](https://github.com/cgb37/dnd-adventure-tpl/commit/690125b180304a9c4957031a4eb82488b1fe2899))
* **encounter:** add provider override to encounter generation ([151742f](https://github.com/cgb37/dnd-adventure-tpl/commit/151742ff16ff27f4977c51c93cf145d2366a3813))
* encounters ([5b5da88](https://github.com/cgb37/dnd-adventure-tpl/commit/5b5da88abc5e90f0219011d4e11fb3a1008ff25f))
* **env:** add example environment variables for campaigns ([18b8b67](https://github.com/cgb37/dnd-adventure-tpl/commit/18b8b6776955ab0ec5d2900f5b019ac471c6cf4e))
* **errors:** add JSON sanitization for error responses ([5d94836](https://github.com/cgb37/dnd-adventure-tpl/commit/5d948363492aaea14a5f2801dee74f404f00b33d))
* **errors:** implement centralized error handling ([e6efc52](https://github.com/cgb37/dnd-adventure-tpl/commit/e6efc52da052f4fe898756c72cee5323460ac450))
* **factory:** add LLM agent builder for multiple providers ([99ca5ae](https://github.com/cgb37/dnd-adventure-tpl/commit/99ca5ae2bdbfcea25318fdc17851915230dc15cd))
* galleries ([99f21d1](https://github.com/cgb37/dnd-adventure-tpl/commit/99f21d168e17960f9ab0fcfd2be650a0d77d1c0c))
* gallery page for locations ([2de3734](https://github.com/cgb37/dnd-adventure-tpl/commit/2de37340d4e0b079a605a11213897c5e86cf8338))
* generate locations data file ([f164d3f](https://github.com/cgb37/dnd-adventure-tpl/commit/f164d3fa814efaeea1b4ac59a238bc25c9604957))
* generate pages data file for locations npcs monsters encounters ([edd3037](https://github.com/cgb37/dnd-adventure-tpl/commit/edd3037ff0e5515b7355846bed7ce70b3b43a9fe))
* **generate_pages_data:** handle missing directory gracefully ([dae357f](https://github.com/cgb37/dnd-adventure-tpl/commit/dae357f6be771ee5fac016f3c56e48ac2d118145))
* **generate:** add AI content generation endpoint ([16bece0](https://github.com/cgb37/dnd-adventure-tpl/commit/16bece02c29efae78821c91642334ce6c0a38669))
* **generate:** add support for LLM provider header ([5238b28](https://github.com/cgb37/dnd-adventure-tpl/commit/5238b28d444be1fd0a24486f35d15e7f76c65dd5))
* **generators:** add AI content generator module ([a96d5b5](https://github.com/cgb37/dnd-adventure-tpl/commit/a96d5b5e8abfe0927c81fbff7e5ccd1275f4afa6))
* **generators:** add title and slug resolution function ([53d8704](https://github.com/cgb37/dnd-adventure-tpl/commit/53d8704afb2fe8fecd96c1fad25bf32ecb79ef40))
* **gitignore:** update ignored paths for clarity ([b47e65c](https://github.com/cgb37/dnd-adventure-tpl/commit/b47e65c2ecbf82c076a2cbad837cb421cb0c7030))
* **health:** add health check endpoint for LLM provider ([da536e6](https://github.com/cgb37/dnd-adventure-tpl/commit/da536e684c17eeeb2ffdf2c703dfab39e226d1b7))
* **ids:** add UUID generation for content identifiers ([454b123](https://github.com/cgb37/dnd-adventure-tpl/commit/454b1234d1afbcffa3f20ceefe537e2aaa9a260a))
* image ([4284cde](https://github.com/cgb37/dnd-adventure-tpl/commit/4284cde3e31fb800d88eb4c47c98cc0e5ff583d8))
* **jekyll:** enhance development environment initialization ([de2855d](https://github.com/cgb37/dnd-adventure-tpl/commit/de2855d49256ad1012368b726fb851dd03ad9dc4))
* **kinds:** add kind normalization function ([1600107](https://github.com/cgb37/dnd-adventure-tpl/commit/1600107d491de869f87a3e4666f5f91044d03c8a))
* layout refactoring ([eac1616](https://github.com/cgb37/dnd-adventure-tpl/commit/eac161675a4df634790bc7857c217246430bba23))
* layouts ([a52afe1](https://github.com/cgb37/dnd-adventure-tpl/commit/a52afe14ba5279e210f0643d4b6ac150750d69e7))
* **limits:** add in-memory rate limiting for API requests ([990fb9d](https://github.com/cgb37/dnd-adventure-tpl/commit/990fb9d0a6ec60ea9771e77086e5208c37ec48b6))
* **llm_api:** add Dockerfile for LLM API service ([13f4120](https://github.com/cgb37/dnd-adventure-tpl/commit/13f41207e1f9a51164b9858d46cab3717443517b))
* **llm_api:** add example environment configuration file ([98c537e](https://github.com/cgb37/dnd-adventure-tpl/commit/98c537e0e43f2c8bd868473d04775b4fb215fe26))
* **llm_api:** add README for AI content generation service ([5acb4c9](https://github.com/cgb37/dnd-adventure-tpl/commit/5acb4c94b5c852e3a0364eafe0705f1a528d4015)), closes [#1](https://github.com/cgb37/dnd-adventure-tpl/issues/1)
* **llm-api:** add initial project configuration ([9d9e3b7](https://github.com/cgb37/dnd-adventure-tpl/commit/9d9e3b7d0aa2f6f27b2fda1c8f7a626986444819))
* **location:** add AI content generator for D&D locations ([6102145](https://github.com/cgb37/dnd-adventure-tpl/commit/610214532d2aaabe1737a2437a49ef1820d1ba23)), closes [#42](https://github.com/cgb37/dnd-adventure-tpl/issues/42)
* **location:** add provider override for location generation ([9617372](https://github.com/cgb37/dnd-adventure-tpl/commit/96173726ddb788e74870b2f86d7304574e989ef6))
* locations toc ([ec16030](https://github.com/cgb37/dnd-adventure-tpl/commit/ec16030d2837ebe9d7866a069271dfd68b725e76))
* **logging:** add structured logging configuration ([687f1cd](https://github.com/cgb37/dnd-adventure-tpl/commit/687f1cd2f9ee57661f93b6dd22552eb1be51d686))
* **meta-api:** add endpoints for generators and providers ([952dd43](https://github.com/cgb37/dnd-adventure-tpl/commit/952dd4303e19a338232c752e658ab66e3bfa9993))
* **middleware:** add body size limit enforcement ([0359c5b](https://github.com/cgb37/dnd-adventure-tpl/commit/0359c5b9593b4b27625b6a103c2077f6f0a5c946))
* **middleware:** add request ID middleware for logging ([9741de6](https://github.com/cgb37/dnd-adventure-tpl/commit/9741de6fc2a77e8fffaf60c74f38136ceb083ca3))
* **models:** add base class for generated drafts ([a3d708a](https://github.com/cgb37/dnd-adventure-tpl/commit/a3d708a143e7e2c689153b85edfd3a293001ff45))
* **monster:** add AI content generator for D&D monsters ([507bb46](https://github.com/cgb37/dnd-adventure-tpl/commit/507bb465d9c0210a9f66b45a3e05c9f297b91667))
* **monster:** add provider override for monster generation ([cac1abd](https://github.com/cgb37/dnd-adventure-tpl/commit/cac1abd73bcd70d3e6865facb63a46ed054d68df))
* new location battle map ([1e4f0f1](https://github.com/cgb37/dnd-adventure-tpl/commit/1e4f0f1fa35c311be2159581ed8b3ca07948786f))
* new locations ([30c37e1](https://github.com/cgb37/dnd-adventure-tpl/commit/30c37e18b5767e1e229cbad70ee5276a9d7121de))
* new NPCs ([28223ed](https://github.com/cgb37/dnd-adventure-tpl/commit/28223ed589370f0aadcd2f083f58c66f43736326))
* npc front matter and layout ([1cef607](https://github.com/cgb37/dnd-adventure-tpl/commit/1cef607d83e326fd4639dd876f9d417937ce649c))
* npc image ([1730328](https://github.com/cgb37/dnd-adventure-tpl/commit/17303283af98c5ee1c1d7a97e09ff1d42ae0c2b0))
* npc tpl ([97094a9](https://github.com/cgb37/dnd-adventure-tpl/commit/97094a9fe51e4deb35370a4f8dd06885636a64e6))
* **npc-generator:** add provider override for NPC generation ([12508ed](https://github.com/cgb37/dnd-adventure-tpl/commit/12508eda756c2c4c2ea559c7bf4672a6440c48af))
* **npc:** add AI content generation for NPC drafts ([db7009e](https://github.com/cgb37/dnd-adventure-tpl/commit/db7009eca59261e7191bdc4e9eb458ba0b3b9733))
* **package:** add initial package configuration for Playwright ([a8d9ca7](https://github.com/cgb37/dnd-adventure-tpl/commit/a8d9ca73fe21587a256916c1d2c317b8ea03fba4))
* **package:** migrate project to new structure ([3efc613](https://github.com/cgb37/dnd-adventure-tpl/commit/3efc613df06220d5346ec0e684c37c8df7ed5752))
* **playwright:** add Playwright configuration for UI tests ([258eee7](https://github.com/cgb37/dnd-adventure-tpl/commit/258eee7e6fdff4896b44f88f53725328b8d7716e))
* **promote_draft:** add script to promote drafts to _pages ([5565f80](https://github.com/cgb37/dnd-adventure-tpl/commit/5565f803b5bda43b2e9f531e61bab3f99d0a6ed5))
* **promote:** add promote endpoint for campaign drafts ([8f67ad1](https://github.com/cgb37/dnd-adventure-tpl/commit/8f67ad13073dc148007aebd9795943915e3aa582))
* **promotion_mapping:** add promotion rules and path functions ([0da1fff](https://github.com/cgb37/dnd-adventure-tpl/commit/0da1fff29a91770b1a9787e9b3f70917a7a359f1))
* **promotion:** implement draft promotion functionality ([304005c](https://github.com/cgb37/dnd-adventure-tpl/commit/304005cafea8f003f4af03da09f63c8077f7c4b6))
* **prompts:** add Figma design prompt for AI chatbot layout ([7389571](https://github.com/cgb37/dnd-adventure-tpl/commit/7389571bce3cba7b96da856b03e241ec94137a09))
* **readme:** add README file for AI content generator ([a99e10b](https://github.com/cgb37/dnd-adventure-tpl/commit/a99e10bed15b5360c9968aafc5fe6702f816786e))
* **registry:** add generator kind handling for UI integration ([b76ca07](https://github.com/cgb37/dnd-adventure-tpl/commit/b76ca074d4e550f7128026b887921743d8f05711))
* **release:** add script for version management and changelog ([4c9c925](https://github.com/cgb37/dnd-adventure-tpl/commit/4c9c925487ef4ecce39708b6521a2c32a40bfc8a))
* **requests:** add GenerateRequest model for API ([7c57285](https://github.com/cgb37/dnd-adventure-tpl/commit/7c57285824b9dc4d953b0a4ec0f05f7c361a0e83)), closes [#1](https://github.com/cgb37/dnd-adventure-tpl/issues/1)
* **responses:** add success response handling functions ([c5ee00e](https://github.com/cgb37/dnd-adventure-tpl/commit/c5ee00ec125fe9014dce243d5786dac98c1599d4))
* **routes:** add LLM API route initialization ([294c740](https://github.com/cgb37/dnd-adventure-tpl/commit/294c74087920e422bd18df263709cac1004fd60c))
* **routes:** add meta and promote routers to app ([7a91263](https://github.com/cgb37/dnd-adventure-tpl/commit/7a912638169ebd9f9460f02883e0c269d36f42c1))
* **scripts:** add future annotations support ([de060a8](https://github.com/cgb37/dnd-adventure-tpl/commit/de060a8b957fd4f9de10366767c0388972cd7dca))
* **scripts:** add new iteration documentation generator ([b063e7e](https://github.com/cgb37/dnd-adventure-tpl/commit/b063e7ebfb7cc2d077155fc7ea5ee2c851210f35))
* **scripts:** add promote-draft script for campaign management ([d0baf5d](https://github.com/cgb37/dnd-adventure-tpl/commit/d0baf5de5d302db5686e1df2c1884552533447f1))
* **security:** add API key authentication middleware ([a602052](https://github.com/cgb37/dnd-adventure-tpl/commit/a60205240bd610277eb8c6b187901ce6b3b235d5))
* **services:** add initial service module for AI content generation ([272fe42](https://github.com/cgb37/dnd-adventure-tpl/commit/272fe429275f23b54b6154d0c8e0eb888f1ccfd9))
* **smoke-api:** add smoke testing script for API validation ([a53e6e9](https://github.com/cgb37/dnd-adventure-tpl/commit/a53e6e9a26f9db47ff4ed0c7f3afbd87abdb270e))
* styles and layout ([e1fb524](https://github.com/cgb37/dnd-adventure-tpl/commit/e1fb5247c3bc7fc1cbd3d93b0bac2a8711e01d38))
* **styles:** add chatbot stylesheet for improved UI ([6e53fe6](https://github.com/cgb37/dnd-adventure-tpl/commit/6e53fe614b4efd076b0add39b3816004bb1beff3))
* **submodule:** add RPG game campaigns as submodules ([4798514](https://github.com/cgb37/dnd-adventure-tpl/commit/479851406053308fa4e05ca49c945b0c97252c62))
* **template:** add D&D campaign template upgrade plan ([77bb7f2](https://github.com/cgb37/dnd-adventure-tpl/commit/77bb7f2c10c9930c25d11734f8d6646a25938c2b))
* **tests:** add conftest.py for shared fixtures ([34c1764](https://github.com/cgb37/dnd-adventure-tpl/commit/34c17644a884ee3bcaa3da9ad0e8ddc7d7545923))
* **tests:** add tests for NPC and monster YAML keys ([a718f49](https://github.com/cgb37/dnd-adventure-tpl/commit/a718f499adf1d10cbbeca2acfa16f059f981dedd))
* **tests:** add UI automation tests for chatbot functionality ([ef6de37](https://github.com/cgb37/dnd-adventure-tpl/commit/ef6de3791fc49f380624d492ae089aba32f05c4d))
* **tests:** add unit test for draft writing functionality ([a912b15](https://github.com/cgb37/dnd-adventure-tpl/commit/a912b159c05c385a9ec1cbabb7f474375e0f4646))
* **types:** add AI content generator type definitions ([69f8959](https://github.com/cgb37/dnd-adventure-tpl/commit/69f8959d8fe0590b5f1b4e3cfbd3f1569de21e7d))
* update enounters.yaml ([3760261](https://github.com/cgb37/dnd-adventure-tpl/commit/37602611c614664ed63136a7cdf9226c181df0d0))
* **use-campaign:** add campaign initialization and demo content features ([c02d448](https://github.com/cgb37/dnd-adventure-tpl/commit/c02d448e64ef162f0b1440f2267c23be7e222a5d))
* **use-campaign:** add campaign management script ([43ce290](https://github.com/cgb37/dnd-adventure-tpl/commit/43ce2904165c62c96c7f9406638cb7ffbf2576f4))
* working on village of bramblewood ([5a29ad4](https://github.com/cgb37/dnd-adventure-tpl/commit/5a29ad4ee3541639fa4d3255f36c6bc39fa4b968))


### BREAKING CHANGES

* **package:** The project structure and configuration have changed, necessitating updates to any dependent tooling or scripts.
* **template:** Campaign content must now be housed in separate repositories rather than the monorepo structure.
* The require_api_key function has been
rewritten, altering its behavior and signature.
* **factory:** The build_agent function signature now includes
an optional provider_override parameter.
* **chatbot:** Provider selection is now passed per request using the header `X-LLM-Provider`.
* **encounter:** New dependencies introduced for AI integration.
* **use-campaign:** The command interface has been modified to include new flags which will require users to adapt their usage accordingly.



