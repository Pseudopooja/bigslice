#!/usr/bin/env python3

import sqlite3
from flask import render_template, request, redirect
from flask import abort
import json
from os import path

# import global config
from ..config import conf

# set blueprint object
from flask import Blueprint
blueprint = Blueprint('bgc', __name__)


@blueprint.route("/dataset/<int:dataset_id>/bgc/<int:bgc_id>")
def page_bgc_no_run(dataset_id, bgc_id):
    return redirect("/dataset/{}/bgc/{}/run/0".format(dataset_id, bgc_id))


@blueprint.route("/dataset/<int:dataset_id>/bgc/<int:bgc_id>/run/<int:run_id>")
def page_bgc(dataset_id, bgc_id, run_id):

    # page title
    with sqlite3.connect(conf["db_path"]) as con:
        cur = con.cursor()

        # redirect if run_id/dataset_id == 0
        redir = False
        if dataset_id < 1:
            # fetch appropriate dataset_id
            dataset_id = cur.execute((
                "select dataset_id"
                " from bgc"
                " where id=?"
            ), (bgc_id, )).fetchall()[0][0]
            redir = True
        if run_id < 1:
            # fetch latest run
            run_id = cur.execute((
                "select id"
                " from run"
                " order by id desc"
                " limit 1"
            )).fetchall()[0][0]
            redir = True
        if redir:
            return redirect("/dataset/{}/bgc/{}/run/{}".format(
                dataset_id, bgc_id, run_id))

        # fetch bgc_name, dataset_name
        bgc_name, dataset_name = cur.execute((
            "select bgc.name, dataset.name"
            " from bgc, dataset"
            " where bgc.id=?"
            " and bgc.dataset_id=?"
            " and bgc.dataset_id=dataset.id"
        ), (bgc_id, dataset_id)).fetchall()[0]

        # fetch taxon for subtitle
        bgc_taxon_name = cur.execute((
            "select taxon.name"
            " from bgc_taxonomy, taxon, bgc"
            " where bgc.id=bgc_taxonomy.bgc_id"
            " and taxon.id=bgc_taxonomy.taxon_id"
            " and bgc.id=?"
            " order by taxon.level desc"
            " limit 1"
        ), (bgc_id, )).fetchall()[:1]

        # set title and subtitle
        page_title = "BGC: {}".format(bgc_name)
        if len(bgc_taxon_name) <= 0:
            page_subtitle = ("From dataset: {}".format(dataset_name))
        else:
            page_subtitle = (
                "From <i>{}</i> (dataset: {})".format(
                    bgc_taxon_name[0][0], dataset_name))

        # status_id
        status_id, = cur.execute((
            "select status"
            " from run"
            " where id = ?"
        ), (run_id, )).fetchall()[0]

        # for run selector dropdown
        run_ids = [row[0] for row
                   in cur.execute((
                       "select id"
                       " from run"
                       " order by id asc"
                   )).fetchall()]

    # render view
    return render_template(
        "bgc/main.html.j2",
        bgc_id=bgc_id,
        dataset_id=dataset_id,
        run_id=run_id,
        run_ids=run_ids,
        status_id=status_id,
        page_title=page_title,
        page_subtitle=page_subtitle
    )

# APIs


@blueprint.route("/api/bgc/get_overview")
def get_bgc_table():
    """ for bgc datatable """
    result = {}
    bgc_id = request.args.get('bgc_id', type=int)

    with sqlite3.connect(conf["db_path"]) as con:
        cur = con.cursor()

        # fetch direct properties
        (folder_path, file_path, on_contig_edge,
         result["length"], result["type"],
         result["type_desc"]) = cur.execute((
             "select orig_folder, orig_filename,"
             " on_contig_edge, length_nt, type,"
             " enum_bgc_type.description"
             " from bgc, enum_bgc_type"
             " where bgc.id=?"
             " and bgc.type=enum_bgc_type.code"
         ), (bgc_id, )).fetchall()[0]
        result["file_path"] = path.join("/", folder_path, file_path)
        result["fragmented"] = "yes" if on_contig_edge == 1 else (
            "no" if on_contig_edge == 0 else "n/a"
        )

        # fetch genes count
        result["genes_count"] = cur.execute((
            "select count(id)"
            " from cds"
            " where bgc_id=?"
        ), (bgc_id, )).fetchall()[0][0]

        # fetch taxonomy information
        result["taxon_desc"] = cur.execute((
            "select level, name"
            " from taxon_class"
            " order by level asc"
        )).fetchall()
        result["taxonomy"] = {
            row[0]: row[1] for row in cur.execute((
                "select level, taxon.name"
                " from taxon, bgc_taxonomy"
                " where taxon.id=bgc_taxonomy.taxon_id"
                " and bgc_taxonomy.bgc_id=?"
            ), (bgc_id, )).fetchall()
        }

        # fetch class information
        result["classes"] = cur.execute((
            "select chem_class.name, chem_subclass.name"
            " from bgc, bgc_class, chem_subclass, chem_class"
            " where bgc.id=bgc_class.bgc_id"
            " and bgc_class.chem_subclass_id=chem_subclass.id"
            " and chem_subclass.class_id=chem_class.id"
            " and bgc.id=?"
        ), (bgc_id, )).fetchall()

    return result