"""Shared feature ordering for research training and live-card inference."""
GROUPS={"baseline_features":(),"ngs":("ngs",),"snap_counts":("snap",),
        "pfr_advanced":("pfr",),"combined":("ngs","snap","pfr"),
        "weekly_workload":("workload",),"opponent_efficiency":("matchup",),
        "workload_matchup":("workload","matchup"),
        "advanced_workload":("ngs","snap","pfr","workload"),
        "advanced_matchup":("ngs","snap","pfr","matchup"),
        "advanced_all":("ngs","snap","pfr","workload","matchup"),
        "pfr_fixed":("pfr_new",),"ftn_player":("ftn",),"ftn_opponent":("ftn_defense",),
        "pfr_ftn":("pfr_new","ftn"),"pfr_plus":("ngs","snap","pfr_new"),
        "ftn_plus":("ngs","snap","ftn"),
        "ftn_opponent_plus":("ngs","snap","matchup","ftn_defense"),
        "pfr_ftn_plus":("ngs","snap","pfr_new","ftn"),
        "all_new":("ngs","snap","matchup","pfr_new","ftn","ftn_defense")}
DIMENSIONS={"ngs":4,"snap":2,"pfr":4,"workload":4,"matchup":4,
            "pfr_new":4,"ftn":4,"ftn_defense":4}
